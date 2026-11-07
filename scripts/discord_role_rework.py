#!/usr/bin/env python3
"""Update existing Egypt Y-DNA role picker and open #new-results for Verified.

Safe preview/apply GitHub action. Preserves existing user messages and assigned
roles. It removes only superseded, bot-owned reaction role picker messages.
Distinct emoji reactions per message stay well below Discord's 20-emoji limit.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from discord_role_menu import (
    SELECTABLE_ORIGINS, SELECTABLE_YDNA, COUNTRY_COLORS,
    menu_groups, menu_content, menu_emojis,
    OVERVIEW_MARKER, overview_text, ROLE_MARKER
)

GID = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
MODE = os.getenv("MODE", "preview").strip().lower()
BASE = "https://discord.com/api/v10"

VIEW = 1 << 10
SEND = 1 << 11
READ = 1 << 16
REACT = 1 << 6
THREADS = 1 << 38

def api(method, path, body=None):
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    for attempt in range(7):
        req = urllib.request.Request(
            BASE + path, method=method, data=payload,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNARoleMenuV2/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                text = res.read()
                time.sleep(0.18)
                return json.loads(text) if text else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            if exc.code == 429 and attempt < 6:
                try:
                    delay = min(30, float(json.loads(detail).get("retry_after", 2)))
                except (ValueError, TypeError):
                    delay = 2
                time.sleep(delay + 0.5)
                continue
            raise RuntimeError(
                f"Discord HTTP {exc.code} {method} {path}: {detail[:350]}") from exc
    raise RuntimeError("Discord rate-limit retries exceeded")

def change(method, path, body, label):
    if MODE == "preview":
        print("[PREVIEW]", label, flush=True)
        return None
    result = api(method, path, body)
    print("[APPLIED]", label, flush=True)
    return result

def overwrite(role_id, allow=0, deny=0, kind=0):
    return {"id": str(role_id), "type": kind,
            "allow": str(allow), "deny": str(deny)}

def secured_permissions(verified_id, staff_ids, bot_id, can_post):
    # @everyone cannot see the private member channels until Verified,
    # even though the channel's parent category may have different overrides.
    result = [overwrite(GID, deny=VIEW | SEND | THREADS)]
    result.append(overwrite(
        verified_id, allow=VIEW | READ | REACT | (SEND | THREADS if can_post else 0),
        deny=0 if can_post else SEND | THREADS))
    result.extend(
        overwrite(role_id, allow=VIEW | SEND | READ | REACT | THREADS)
        for role_id in staff_ids
    )
    result.append(overwrite(
        bot_id, allow=VIEW | SEND | READ | REACT | THREADS, kind=1))
    return result

def norm(overwrites):
    return sorted(
        (str(o["id"]), int(o["type"]),
         int(o.get("allow", "0")), int(o.get("deny", "0")))
        for o in overwrites
    )

def get_messages(channel_id, pages=2):
    gathered = []
    before = None
    for _ in range(pages):
        path = f"/channels/{channel_id}/messages?limit=100"
        if before:
            path += "&before=" + before
        batch = api("GET", path)
        gathered.extend(batch or [])
        if len(batch or []) < 100:
            break
        before = str(batch[-1]["id"])
    return gathered

def ensure_menu(channel_id, marker, content, choices, messages, bot_id):
    # Reuse only content-identical V2 menus. If a menu's contents change,
    # replace it entirely to avoid old reactions mapping to different roles.
    mine = next((m for m in messages
                 if str(m.get("author", {}).get("id")) == str(bot_id)
                 and marker in m.get("content", "")), None)
    if mine and mine.get("content") != content:
        change("DELETE", f"/channels/{channel_id}/messages/{mine['id']}",
               None, "remove outdated menu before changing its emoji mapping")
        mine = None
    if not mine:
        mine = change("POST", f"/channels/{channel_id}/messages",
                      {"content": content, "allowed_mentions": {"parse": []}},
                      "publish role menu " + marker)
    if MODE == "apply" and mine:
        seen = {r.get("emoji", {}).get("name") for r in mine.get("reactions", [])}
        for emoji in choices:
            if emoji not in seen:
                api("PUT", f"/channels/{channel_id}/messages/{mine['id']}/"
                    f"reactions/{urllib.parse.quote(emoji, safe='')}/@me")
        print("[READY] reaction choices:", len(choices), marker, flush=True)
    return mine

def main():
    if MODE not in ("preview", "apply"):
        raise ValueError("MODE must be preview or apply")
    if not GID.isdecimal() or not TOKEN:
        raise ValueError("Missing GitHub Secrets DISCORD_GUILD_ID / DISCORD_BOT_TOKEN")
    guild = api("GET", f"/guilds/{GID}")
    bot = api("GET", "/users/@me")
    roles = api("GET", f"/guilds/{GID}/roles")
    channels = api("GET", f"/guilds/{GID}/channels")
    names = {r["name"].casefold(): r for r in roles}
    verified = names.get("verified")
    if not verified:
        raise RuntimeError("Verified role missing. Run verification setup first.")
    staff_ids = [
        str(names[name]["id"])
        for name in ("founder", "administrator", "moderator") if name in names
    ]
    print("[SERVER]", guild["name"], "| mode", MODE)
    print("[GOAL] Flag-based origins, detailed single-branch Y-DNA, member posts in #new-results.")

    print("1) Create only missing country roles. Existing roles remain untouched.")
    for name in SELECTABLE_ORIGINS:
        if name.casefold() in names:
            print("[EXISTS]", name)
            continue
        if name not in COUNTRY_COLORS:
            print("[WARNING] Origin role missing:", name,
                  "— skipping until created manually.")
            continue
        made = change("POST", f"/guilds/{GID}/roles",
                      {"name": name, "color": COUNTRY_COLORS[name],
                       "permissions": "0", "mentionable": False, "hoist": False},
                      "create new country role: " + name)
        if made:
            names[name.casefold()] = made
    print("2) Verify Y-DNA subgroups and neutral role permissions.")
    for name in SELECTABLE_YDNA:
        if name.casefold() not in names:
            print("[WARNING] Missing DNA branch role:", name)
    unsafe = set()
    for name in list(SELECTABLE_ORIGINS) + list(SELECTABLE_YDNA) + ["Male", "Female"]:
        role = names.get(name.casefold())
        if not role:
            continue
        perms = int(role.get("permissions", "0"))
        if not perms:
            continue
        print("[SECURITY] Existing selectable role has server powers:",
              name, "permission_bits=", perms, flush=True)
        if MODE == "preview":
            print("[PREVIEW] Reset this role to zero extra permissions:", name)
        else:
            try:
                change("PATCH", f"/guilds/{GID}/roles/{role['id']}",
                       {"permissions": "0"},
                       "remove dangerous permissions from selectable role: " + name)
                role["permissions"] = "0"
            except RuntimeError as error:
                unsafe.add(name.casefold())
                print("[ACTION REQUIRED] Cannot secure", name,
                      "- role will NOT be offered or auto-granted until the "
                      "owner manually removes all role permissions:", error,
                      flush=True)
    if MODE == "preview":
        planned = {**names}
        for name in SELECTABLE_ORIGINS:
            planned.setdefault(name.casefold(), {"name": name, "permissions": "0"})
    else:
        planned = {key: role for key, role in names.items() if key not in unsafe}

    picker = next((c for c in channels if c.get("type") == 0
                   and c["name"] == "choose-roles"), None)
    if not picker:
        community = next((c for c in channels if c.get("type") == 4
                          and "COMMUNITY" in c["name"]), None)
        payload = {
            "name": "choose-roles", "type": 0,
            "topic": "Pick your own origin, detailed Y-DNA and optional gender roles.",
            "permission_overwrites": secured_permissions(
                str(verified["id"]), staff_ids, bot["id"], False),
        }
        if community: payload["parent_id"] = str(community["id"])
        picker = change("POST", f"/guilds/{GID}/channels", payload,
                        "create Verified-only #choose-roles")
    if picker:
        desired = secured_permissions(str(verified["id"]), staff_ids, bot["id"], False)
        if norm(picker.get("permission_overwrites", [])) != norm(desired):
            change("PATCH", f"/channels/{picker['id']}",
                   {"permission_overwrites": desired},
                   "secure #choose-roles as Verified-only, reaction-enabled and read-only")

    print("3) Publish one pinned overview and compact, themed reaction menus.")
    groups = menu_groups(planned)
    print("[CHECK] Menu sections:", len(groups),
          "| origin roles", len(SELECTABLE_ORIGINS),
          "| detailed Y-DNA roles", len(SELECTABLE_YDNA))
    if MODE == "preview":
        for marker, category, options in groups:
            print("[PREVIEW]", marker, "|", len(options), "emoji choices")
        print("[PREVIEW] Pin one short overview, and remove only old bot picker posts")
    elif picker:
        cid = str(picker["id"])
        messages = get_messages(cid)
        # Publish menu messages first, then the overview so it is the most
        # recently sent / easily discoverable message in Discord.
        for marker, category, options in groups:
            ensure_menu(cid, marker, menu_content(marker, category, options),
                        menu_emojis(category, options), messages, bot["id"])
        overview = next((m for m in messages
                         if str(m.get("author", {}).get("id")) == str(bot["id"])
                         and OVERVIEW_MARKER in m.get("content", "")), None)
        message_text = overview_text(groups)
        if overview:
            if overview.get("content") != message_text:
                change("PATCH", f"/channels/{cid}/messages/{overview['id']}",
                       {"content": message_text, "allowed_mentions": {"parse": []}},
                       "refresh compact role picker overview")
        else:
            overview = change("POST", f"/channels/{cid}/messages",
                              {"content": message_text, "allowed_mentions": {"parse": []}},
                              "publish single overview and instructions")
        if overview:
            try:
                api("PUT", f"/channels/{cid}/pins/{overview['id']}")
                print("[PINNED] role picker overview")
            except RuntimeError as error:
                print("[NOTICE] Could not pin overview (optional):", error)
        # Historical picker posts are bot-generated and can safely be
        # removed; existing member role assignments are not touched.
        for old in messages:
            if str(old.get("author", {}).get("id")) != str(bot["id"]):
                continue
            body = old.get("content", "")
            if ("**EGYPT Y-DNA ROLE SELECTION:" in body or
                    "**EGYPT Y-DNA PICKER V1:" in body):
                change("DELETE", f"/channels/{cid}/messages/{old['id']}",
                       None, "remove obsolete, bot-owned numeric reaction menu")

    print("4) Allow ALL Verified members to post in #new-results.")
    results = next((c for c in channels if c.get("type") == 0
                    and c.get("name") == "new-results"), None)
    if results:
        overrides = secured_permissions(str(verified["id"]), staff_ids,
                                        bot["id"], True)
        data = {
            "permission_overwrites": overrides,
            "topic": "All Verified members can post Egyptian Y-DNA discoveries with sources. Keep personal genetic information private.",
        }
        if norm(results.get("permission_overwrites", [])) != norm(overrides):
            change("PATCH", f"/channels/{results['id']}", data,
                   "make #new-results writable for every Verified member")
        else:
            print("[EXISTS] #new-results already lets Verified members post")
        if MODE == "apply":
            existing = get_messages(results["id"], 1)
            intro = ("🧬 **NEW EGYPTIAN Y-DNA RESULTS — COMMUNITY SUBMISSIONS**\n"
                     "Every **Verified** member may post new Egyptian Y-DNA results.\n"
                     "Please include the **terminal SNP, test type, public source, "
                     "and governorate** (when known and authorized).\n"
                     "Label uncertain or predicted results clearly. No private "
                     "kit information or personal data without permission.")
            my_old = next((m for m in existing
                           if str(m.get("author", {}).get("id")) == str(bot["id"])
                           and ("**Confirmed Egyptian Y-DNA results**" in m.get("content", "")
                                or "**NEW EGYPTIAN Y-DNA RESULTS — COMMUNITY SUBMISSIONS**"
                                   in m.get("content", ""))), None)
            if my_old:
                if my_old.get("content") != intro:
                    change("PATCH", f"/channels/{results['id']}/messages/{my_old['id']}",
                           {"content": intro, "allowed_mentions": {"parse": []}},
                           "update staff-only old posting description")
            else:
                change("POST", f"/channels/{results['id']}/messages",
                       {"content": intro, "allowed_mentions": {"parse": []}},
                       "publish community posting guidelines")
    else:
        print("[WARNING] No text #new-results found; no channel created or changed.")

    print("DONE. No staff role is self-assignable. Old generic letter roles are "
          "no longer offered, but existing members/role history are preserved.")
    if MODE == "preview":
        print("PREVIEW ONLY. Select apply to make these changes.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
