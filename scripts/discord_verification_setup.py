#!/usr/bin/env python3
"""Egypt Y-DNA automatic membership setup without a mandatory rules popup.

Default preview is read-only. Apply:
- creates/updates Male, Female, Verified and Bot role labels,
- preserves #welcome and the official rules channel for incoming members,
- privately archives former #verification and #verification-chat (no deletions),
- keeps all normal channels Verified-only and all STAFF channels staff-only,
- retains role-picker access and Carl-bot's designated channel exception.

The scheduled discord_member_verification.py worker automatically assigns Verified
to joined human accounts. Rules are informational; no checkbox or staff approval.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from discord_role_menu import menu_groups, menu_content, menu_emojis
from discord_join_feed import JOIN_NAME, read_only_permissions

BASE = "https://discord.com/api/v10"
GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
MODE = os.getenv("MODE", "preview").strip().lower()
VIEW = 1 << 10
SEND = 1 << 11
READ = 1 << 16
REACT = 1 << 6
THREAD_SEND = 1 << 38
ADMIN = 1 << 3
MANAGE_ROLES = 1 << 28
MANAGE_CHANNELS = 1 << 4

SPECIAL = {
    "Verified": 0x27AE60,
    "Male": 0x337EC7,
    "Female": 0xE36A9D,
    "Bot": 0x26B6BF,
}
STAFF_NAMES = ("Founder", "Administrator", "Moderator")
PRE_VISIBLE = ("welcome", "rules")
READ_ONLY = {
    "welcome", "rules", "verification", "announcements", "server-guide",
    "project-map", "useful-links", "ydna-map"
}
WELCOME_PROMPT = (
    "👋 **EGYPT Y-DNA — WELCOME**\n"
    "Please read #rules before participating. No rules popup is required.\n"
    "Your **Verified** role is assigned automatically by our "
    "scheduled bot (usually within a few minutes). No moderator application "
    "or extra reaction is required.\n"
    "After verification, all public community, origin and Y-DNA channels "
    "become visible. The STAFF category remains private."
)

def api(method, path, data=None):
    body = json.dumps(data).encode() if data is not None else None
    for attempt in range(7):
        req = urllib.request.Request(
            BASE + path, data=body, method=method,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNAVerificationSetup/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                raw = res.read()
                time.sleep(0.12)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as ex:
            message = ex.read().decode(errors="replace")
            if ex.code == 429 and attempt < 6:
                try: pause = min(30, float(json.loads(message).get("retry_after", 2)))
                except (ValueError, TypeError): pause = 2
                time.sleep(pause + 0.6)
                continue
            raise RuntimeError(f"Discord {ex.code} {method} {path}: {message[:400]}")
    raise RuntimeError("Rate limit retries exhausted")

def change(method, path, data, label):
    if MODE == "preview":
        print("[PREVIEW]", label, flush=True)
        return None
    result = api(method, path, data)
    print("[APPLIED]", label, flush=True)
    return result

def overwrite(role_id, allow=0, deny=0, kind=0):
    return {"id": str(role_id), "type": kind,
            "allow": str(allow), "deny": str(deny)}

def policy(style, verified_id, staff_ids, bot_id, is_readonly=False):
    if style == "staff":
        rules = [overwrite(GUILD, deny=VIEW | SEND | THREAD_SEND)]
        rules += [overwrite(id, allow=VIEW | SEND | READ | THREAD_SEND)
                  for id in staff_ids]
        rules.append(overwrite(bot_id, allow=VIEW | SEND | READ | THREAD_SEND, kind=1))
        return rules
    if style == "verification-chat":
        rules = [overwrite(GUILD, allow=VIEW | SEND | READ | THREAD_SEND)]
    elif style == "verification":
        rules = [overwrite(GUILD, allow=VIEW | READ | REACT, deny=SEND | THREAD_SEND)]
    elif style == "public":
        rules = [overwrite(GUILD, allow=VIEW | READ, deny=SEND | THREAD_SEND)]
    elif style == "category":
        rules = [overwrite(GUILD, deny=VIEW | SEND | THREAD_SEND),
                 overwrite(verified_id, allow=VIEW | SEND | THREAD_SEND | READ)]
    else:
        rules = [overwrite(GUILD, deny=VIEW | SEND | THREAD_SEND),
                 overwrite(verified_id,
                           allow=VIEW | READ | REACT |
                                 (0 if is_readonly else SEND | THREAD_SEND),
                           deny=(SEND | THREAD_SEND if is_readonly else 0))]
    for id in staff_ids:
        rules.append(overwrite(id, allow=VIEW | SEND | READ | REACT | THREAD_SEND))
    rules.append(overwrite(bot_id, allow=VIEW | SEND | READ | REACT | THREAD_SEND, kind=1))
    return rules

def exact_overwrites(channel, target):
    current = channel.get("permission_overwrites", [])
    def normalized(arr):
        return sorted(((str(x["id"]), int(x["type"]),
                        int(x.get("allow", 0)), int(x.get("deny", 0)))
                       for x in arr))
    return normalized(current) == normalized(target)

def most_recent(channel_id):
    return api("GET", f"/channels/{channel_id}/messages?limit=100") or []

def sync_message(channel_id, marker, contents, bot_id):
    if MODE == "preview":
        print("[PREVIEW] ensure updated message:", marker)
        return None
    messages = most_recent(channel_id)
    mine = next((m for m in messages
                 if str(m.get("author", {}).get("id")) == str(bot_id)
                 and marker in m.get("content", "")), None)
    if mine:
        if mine.get("content") != contents:
            change("PATCH", f"/channels/{channel_id}/messages/{mine['id']}",
                   {"content": contents, "allowed_mentions": {"parse": []}},
                   "update bot message: " + marker)
        return mine["id"]
    made = change("POST", f"/channels/{channel_id}/messages",
                  {"content": contents, "allowed_mentions": {"parse": []}},
                  "create bot message: " + marker)
    return str(made["id"]) if made else None

def main():
    if MODE not in ("preview", "apply"):
        raise ValueError("Use MODE=preview or apply")
    if not TOKEN or not GUILD.isdecimal():
        raise ValueError("Missing GitHub Secrets DISCORD_BOT_TOKEN and DISCORD_GUILD_ID")
    bot = api("GET", "/users/@me")
    guild = api("GET", f"/guilds/{GUILD}")
    roles = api("GET", f"/guilds/{GUILD}/roles")
    channels = api("GET", f"/guilds/{GUILD}/channels")
    carl_role = next(
        (r for r in roles if r.get("managed") and r.get("tags", {}).get("bot_id")
         and "carl" in r.get("name", "").casefold()
         and "bot" in r.get("name", "").casefold()), None)
    carl_id = str(carl_role["tags"]["bot_id"]) if carl_role else None
    by_name = {r["name"].casefold(): r for r in roles}
    bot_member = api("GET", f"/guilds/{GUILD}/members/{bot['id']}")
    role_by_id = {str(r["id"]): r for r in roles}
    bot_high = max((int(role_by_id[i]["position"]) for i in bot_member.get("roles", [])
                   if i in role_by_id), default=-1)
    if not bot_high:
        raise RuntimeError("The bot has no assignable role above @everyone.")
    bot_permissions = 0
    for role_id in [GUILD] + bot_member.get("roles", []):
        if str(role_id) in role_by_id:
            bot_permissions |= int(role_by_id[str(role_id)].get("permissions", 0))
    if not (bot_permissions & MANAGE_ROLES or bot_permissions & ADMIN):
        raise RuntimeError("Egypt YDNA Bot needs Manage Roles to grant Verified and Bot.")
    if bot_permissions & ADMIN:
        print("[SECURITY WARNING] The bot has full Discord Administrator access. "
              "After setup, remove Administrator from Egypt YDNA Bot and KEEP "
              "Manage Roles, Manage Channels and the message permissions required "
              "for ongoing verification.", flush=True)

    print("Server:", guild["name"], "| mode:", MODE, flush=True)
    staff_ids = []
    for name in STAFF_NAMES:
        role = by_name.get(name.casefold())
        if not role:
            raise RuntimeError("Missing staff role " + name + " - run initial setup first")
        staff_ids.append(str(role["id"]))

    print("1) Special roles: Male, Female, Verified and Bot (and no others).")
    for name, color in SPECIAL.items():
        role = by_name.get(name.casefold())
        if role is None:
            created = change("POST", f"/guilds/{GUILD}/roles",
                {"name": name, "color": color, "permissions": "0", "mentionable": False},
                "create neutral role: " + name)
            if created:
                roles.append(created)
                by_name[name.casefold()] = created
        else:
            updates = {}
            if int(role.get("color", 0)) != color:
                updates["color"] = color
            if int(role.get("permissions", 0)) != 0:
                updates["permissions"] = "0"
            if updates:
                try:
                    change("PATCH", f"/guilds/{GUILD}/roles/{role['id']}",
                           updates, "make " + name + " role neutral and set color")
                except RuntimeError as exc:
                    raise RuntimeError(
                        "Cannot secure the " + name + " role. As server owner, "
                        "set its permissions to zero and keep it below the bot "
                        "in Discord > Server Settings > Roles, then rerun. " +
                        str(exc)) from exc
    # Explicitly remove only the unwanted gender/opt-out roles. Never remove
    # any other existing origin, lineage, staff or membership role.
    obsolete_names = {"non-binary", "nonbinary", "other / non-binary",
                      "prefer not to say"}
    for obsolete in list(roles):
        if obsolete.get("name", "").casefold() in obsolete_names:
            if obsolete.get("managed"):
                print("[NOTICE] Skipping Discord-managed obsolete role:",
                      obsolete["name"])
                continue
            try:
                change("DELETE", f"/guilds/{GUILD}/roles/{obsolete['id']}", None,
                       "remove unwanted role: " + obsolete["name"])
                if MODE == "apply":
                    roles.remove(obsolete)
                    by_name.pop(obsolete["name"].casefold(), None)
            except RuntimeError as exc:
                print("[ACTION REQUIRED] Could not remove unwanted role ",
                      obsolete["name"], ": ", exc,
                      ". The server owner can delete this role manually.",
                      flush=True)

    if MODE == "preview" and "verified" not in by_name:
        print("[PREVIEW] Verified role must be created before channel permissions can be applied.")
    verified = by_name.get("verified")
    if MODE == "apply" and not verified:
        raise RuntimeError("Cannot gate channels until Verified is created.")
    vid = str(verified["id"]) if verified else "000000000000000000"

    print("2) Welcome/rules only: automatic membership without rules popup.")
    if "MEMBER_VERIFICATION_GATE_ENABLED" in guild.get("features", []):
        print("[NOTICE] Native Discord Rules Screening is still enabled. "
              "If you want no popup, disable it in Discord server settings. "
              "The automation does not require it.", flush=True)
    category = next((c for c in channels if c["type"] == 4 and
                     c["name"] in ("🛡️ VERIFICATION", "✅ VERIFICATION")), None)
    if not category:
        category = change("POST", f"/guilds/{GUILD}/channels",
            {"name": "🛡️ VERIFICATION", "type": 4,
             "permission_overwrites": policy("public", vid, staff_ids, bot["id"])},
            "create VERIFICATION category")
        if category: channels.append(category)
    if not category and MODE == "preview":
        print("[PREVIEW] category will be created on apply.")

    for name in PRE_VISIBLE:
        # Always retain the official upper rules channel instead of selecting
        # another same-named #rules channel by API return order.
        if name == "rules" and guild.get("rules_channel_id"):
            channel = next((c for c in channels if c["type"] == 0 and
                            str(c["id"]) == str(guild["rules_channel_id"])), None)
        else:
            channel = next((c for c in channels if c["type"] == 0
                            and c["name"] == name), None)
        style = "public"
        allowed = policy(style, vid, staff_ids, bot["id"])
        if channel:
            diff = {}
            if name != "rules" and category and str(channel.get("parent_id")) != str(category["id"]):
                # Keep the existing upper Community #rules channel in place.
                diff["parent_id"] = str(category["id"])
            if not exact_overwrites(channel, allowed):
                diff["permission_overwrites"] = allowed
            if diff:
                change("PATCH", f"/channels/{channel['id']}", diff,
                       "show pre-verification room #" + name)
                if MODE == "apply": channel.update(diff)
        else:
            data = {"type": 0, "name": name,
                    "permission_overwrites": allowed}
            if category: data["parent_id"] = str(category["id"])
            channel = change("POST", f"/guilds/{GUILD}/channels", data,
                             "create pre-verification #" + name)
            if channel: channels.append(channel)

    # The old moderator-approval rooms are no longer needed. Move them to
    # private STAFF storage, preserving messages/history. They must not remain
    # accessible to newcomers or to ordinary Verified users.
    staff_cat_for_archive = next(
        (c for c in channels if c["type"] == 4 and
         c["name"] in ("🔒 STAFF", "🔒 STAFF ONLY")), None)
    for original in ("verification", "verification-chat"):
        old_channel = next((c for c in channels if c["type"] == 0 and
                            c["name"] == original), None)
        if not old_channel:
            continue
        if not staff_cat_for_archive:
            raise RuntimeError(
                "Private STAFF category is missing. No old verification "
                "channels will be archived publicly. Run the initial "
                "Discord setup to restore STAFF first.")
        new_name = "archived-" + original
        target_overrides = policy("staff", vid, staff_ids, bot["id"])
        change("PATCH", f"/channels/{old_channel['id']}",
               {"name": new_name, "parent_id": str(staff_cat_for_archive["id"]),
                "permission_overwrites": target_overrides},
               "privately archive old #" + original +
               " (no messages deleted)")
        if MODE == "apply":
            old_channel.update({
                "name": new_name,
                "parent_id": str(staff_cat_for_archive["id"]),
                "permission_overwrites": target_overrides
            })
    welcome = next((c for c in channels if c["type"] == 0 and
                    c["name"] == "welcome"), None)
    if welcome:
        sync_message(welcome["id"], "**EGYPT Y-DNA — WELCOME**",
                     WELCOME_PROMPT, bot["id"])

    print("3) Restrict every other channel to Verified, except private STAFF.")
    staff_cat = next((c for c in channels if c["type"] == 4 and
                      c["name"] in ("🔒 STAFF", "🔒 STAFF ONLY")), None)
    verify_cat_id = str(category["id"]) if category else None
    staff_cat_id = str(staff_cat["id"]) if staff_cat else None

    # Ensure people with special pre-existing origin/haplo roles cannot exploit
    # unsafe global administrative permissions to bypass channel visibility.
    security_issue = False
    from discord_server_redesign import ORIGIN, HAPLOS
    from discord_staff_and_roles import LEGACY_ORIGINS
    untrusted = {n.casefold() for n in ORIGIN + HAPLOS + list(LEGACY_ORIGINS)}
    for role in roles:
        if role["name"].casefold() in untrusted:
            high = int(role.get("permissions", 0)) & (ADMIN | MANAGE_ROLES | MANAGE_CHANNELS)
            if high:
                security_issue = True
                print("[SECURITY WARNING] Non-staff role", role["name"],
                      "has unsafe administration flags", high,
                      ". Server owner should remove them.")
    if security_issue:
        print("[SECURITY WARNING] Access cannot be fully guaranteed while "
              "old self-selection roles retain elevated permissions.")

    # A role with Discord Administrator can bypass all channel overwrites.
    # Only intended staff must have that flag; warn for other unknown roles.
    for role in roles:
        if not role.get("managed") and role["name"] not in STAFF_NAMES:
            if int(role.get("permissions", 0)) & ADMIN:
                print("[SECURITY WARNING] Non-staff role", role["name"],
                      "has ADMINISTRATOR and can bypass channel privacy.")

    def picker_permissions():
        result = policy("normal", vid, staff_ids, bot["id"], is_readonly=True)
        if carl_id:
            # Member-level exception grants Carl-bot only view/read/reaction
            # rights on the picker, not access to STAFF and not to @everyone.
            result.append(overwrite(carl_id, allow=VIEW | READ | REACT, kind=1))
        return result

    for channel in channels:
        name = channel["name"]
        is_category = channel["type"] == 4
        inside_staff = staff_cat_id and (
            str(channel.get("parent_id")) == staff_cat_id or str(channel["id"]) == staff_cat_id)
        inside_verification = verify_cat_id and (
            str(channel.get("parent_id")) == verify_cat_id or str(channel["id"]) == verify_cat_id)
        if name in PRE_VISIBLE and channel["type"] == 0:
            continue
        if inside_staff:
            style = "staff"
        elif inside_verification and is_category:
            # The category itself must remain visible to new arrivals.
            style = "public"
        elif inside_verification:
            # Unknown extra rooms under VERIFICATION remain Verified-only.
            style = "normal"
        elif is_category:
            style = "category"
        else:
            style = "normal"
        readonly = name in READ_ONLY or name == "choose-roles"
        intended = (
            read_only_permissions(GUILD, vid, staff_ids, bot["id"])
            if channel["type"] == 0 and name == JOIN_NAME else
            picker_permissions()
            if channel["type"] == 0 and name == "choose-roles" else
            policy(style, vid, staff_ids, bot["id"], is_readonly=readonly)
        )
        if not exact_overwrites(channel, intended):
            change("PATCH", f"/channels/{channel['id']}",
                   {"permission_overwrites": intended},
                   "set Verified gate for " + name + (" [STAFF only]" if inside_staff else ""))
            if MODE == "apply": channel["permission_overwrites"] = intended

    # #choose-roles is a Verified-only channel, including gender self-selection.
    choose = next((c for c in channels if c["type"] == 0 and
                   c["name"] == "choose-roles"), None)
    if not choose:
        community = next((c for c in channels if c["type"] == 4 and
                          c["name"] in ("🌍 COMMUNITY", "💬 COMMUNITY")), None)
        data = {"name": "choose-roles", "type": 0,
                "permission_overwrites": picker_permissions()}
        if community: data["parent_id"] = str(community["id"])
        choose = change("POST", f"/guilds/{GUILD}/channels", data,
                        "create Verified-only #choose-roles")
        if choose: channels.append(choose)
    elif not exact_overwrites(choose, picker_permissions()):
        change("PATCH", f"/channels/{choose['id']}",
               {"permission_overwrites": picker_permissions()},
               "secure #choose-roles behind Verified while letting Carl-bot read it")

    if choose and MODE == "apply":
        role_map = {r["name"].casefold(): r for r in roles}
        existing = most_recent(choose["id"])
        for marker, kind, names in menu_groups(role_map):
            body = menu_content(marker, kind, names)
            found = next((m for m in existing
                          if str(m.get("author", {}).get("id")) == str(bot["id"])
                          and marker in m.get("content", "")), None)
            if found:
                message_id = str(found["id"])
                if found.get("content") != body:
                    change("PATCH", f"/channels/{choose['id']}/messages/{message_id}",
                           {"content": body, "allowed_mentions": {"parse": []}},
                           "update role menu " + marker)
            else:
                created = change("POST", f"/channels/{choose['id']}/messages",
                                 {"content": body, "allowed_mentions": {"parse": []}},
                                 "post role menu " + marker)
                message_id = str(created["id"])
            for emoji in menu_emojis(kind, names):
                api("PUT", f"/channels/{choose['id']}/messages/{message_id}"
                    f"/reactions/{urllib.parse.quote(emoji, safe='')}/@me")
    elif MODE == "preview":
        print("[PREVIEW] Prepare ORIGIN, Y-DNA and GENDER role picker posts.")

    # Put VERIFICATION first, then COMMUNITY/RESEARCH/RESOURCES/STAFF.
    ordered_names = ["🛡️ VERIFICATION", "📌 START HERE", "📌 INFORMATION",
                     "🌍 COMMUNITY", "💬 COMMUNITY",
                     "🧬 Y-DNA RESEARCH", "🧬 Y-DNA RESULTS",
                     "🗺️ RESOURCES", "🗺️ EGYPTIAN ORIGINS",
                     "🔒 STAFF", "🔒 STAFF ONLY"]
    ordered = sorted((c for c in channels if c["type"] == 4),
                     key=lambda c: ordered_names.index(c["name"])
                     if c["name"] in ordered_names else 90)
    if ordered:
        change("PATCH", f"/guilds/{GUILD}/channels",
               [{"id": str(c["id"]), "position": i} for i, c in enumerate(ordered)],
               "position VERIFICATION first, COMMUNITY above RESEARCH, STAFF last")

    if MODE == "apply":
        current_bot = api("GET", f"/guilds/{GUILD}/members/{bot['id']}")
        bot_role = by_name.get("bot")
        if bot_role and str(bot_role["id"]) not in {
                str(r) for r in current_bot.get("roles", [])}:
            change("PUT", f"/guilds/{GUILD}/members/{bot['id']}/roles/{bot_role['id']}",
                   None, "automatically give Egypt YDNA Bot the Bot label")

    print("DONE. Access: new members can read #welcome and #rules, "
          "after joining and the scheduled role scan they get "
          "Verified and all normal channels. STAFF stays private. "
          "No moderator review is required. GitHub is scheduled and "
          "cannot assign the role instantly.")
    if MODE == "preview":
        print("PREVIEW ONLY: no Discord changes made.")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
