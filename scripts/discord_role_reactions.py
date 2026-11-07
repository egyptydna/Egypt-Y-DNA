#!/usr/bin/env python3
"""Free, scheduled self-service Discord roles.

Members react to the role menus in #choose-roles. The worker grants only
whitelisted origin, detailed Y-DNA and Male/Female roles, and never Founder,
Administrator, Moderator, Member, Contributor or Verified Tester.
Reaction removal does not revoke an already assigned role; request staff.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from discord_role_menu import menu_groups, menu_content, menu_emojis

GID = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
BASE = "https://discord.com/api/v10"

def api(method, path, data=None, missing_ok=False):
    raw = json.dumps(data).encode() if data is not None else None
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + path, data=raw, method=method,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNARoleSelector/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as reply:
                content = reply.read()
                time.sleep(0.12)
                return json.loads(content) if content else None
        except urllib.error.HTTPError as ex:
            body = ex.read().decode(errors="replace")
            if ex.code == 429 and attempt < 5:
                try: delay = min(30, float(json.loads(body).get("retry_after", 2)))
                except (TypeError, ValueError): delay = 2
                time.sleep(delay + 0.5)
                continue
            if ex.code == 404 and missing_ok:
                return None
            raise RuntimeError(f"{method} {path}: Discord HTTP {ex.code}: {body[:350]}")
    raise RuntimeError("Discord API rate-limit retries exhausted")

def react_users(channel_id, message_id, emoji):
    after = None
    while True:
        path = (f"/channels/{channel_id}/messages/{message_id}"
                f"/reactions/{urllib.parse.quote(emoji, safe='')}?limit=100")
        if after:
            path += "&after=" + after
        entries = api("GET", path)
        if not entries:
            return
        for item in entries:
            if not item.get("bot"):
                yield str(item["id"])
        if len(entries) < 100:
            return
        after = str(entries[-1]["id"])

def main():
    if not GID.isdecimal() or not TOKEN:
        raise ValueError("Set DISCORD_GUILD_ID and DISCORD_BOT_TOKEN GitHub Secrets")
    guild = api("GET", f"/guilds/{GID}")
    bot = api("GET", "/users/@me")
    roles = api("GET", f"/guilds/{GID}/roles")
    by_name = {r["name"].casefold(): r for r in roles}
    roles_by_id = {str(role["id"]): role for role in roles}
    our_member = api("GET", f"/guilds/{GID}/members/{bot['id']}")
    our_role_ids = {str(role_id) for role_id in our_member.get("roles", [])}
    our_position = max(
        (int(roles_by_id[role_id]["position"]) for role_id in our_role_ids
         if role_id in roles_by_id), default=0)
    our_permissions = 0
    for role_id in our_role_ids | {GID}:
        if role_id in roles_by_id:
            our_permissions |= int(roles_by_id[role_id].get("permissions", 0))
    if not our_permissions & ((1 << 28) | (1 << 3)):
        raise RuntimeError(
            "Egypt YDNA Bot lacks Manage Roles. Enable it on the Bot role in Discord.")
    print("[CHECK] Server:", guild["name"],
          "| Egypt YDNA Bot top role position:", our_position, flush=True)
    member = by_name.get("verified")
    if not member:
        print("SKIP: Verified role missing, run Verification Setup first")
        return
    channels = api("GET", f"/guilds/{GID}/channels")
    selector = next((c for c in channels if c.get("name") == "choose-roles"
                     and c.get("type") == 0), None)
    if not selector:
        print("SKIP: #choose-roles has not been created yet")
        return
    messages = api("GET", f"/channels/{selector['id']}/messages?limit=100")
    own_messages = [m for m in messages or [] if
                    str(m.get("author", {}).get("id")) == str(bot["id"])]
    cache = {}
    examined = assigned = errors = 0
    ignored_unverified = ignored_unmanageable = stale_menus = 0
    print("[CHECK] Found", len(messages or []),
          "recent messages in #choose-roles; applying role selections.")
    allowed_names = set(
        name for _, _, names in menu_groups(by_name) for name in names
    )

    gender_groups = [entry for entry in menu_groups(by_name) if entry[1] == "GENDER"]
    gender_conflicts = set()
    for gender_marker, gender_category, gender_names in gender_groups:
        gender_menu = next(
            (m for m in own_messages if gender_marker in m.get("content", "")), None)
        if not gender_menu:
            continue
        picks = {}
        for gender_name, symbol in zip(gender_names, menu_emojis("GENDER", gender_names)):
            if gender_name not in ("Male", "Female"):
                continue
            for person in react_users(selector["id"], gender_menu["id"], symbol):
                picks.setdefault(person, set()).add(gender_name)
        gender_conflicts.update(person for person, choices in picks.items()
                                if len(choices) > 1)
    if gender_conflicts:
        print("Gender selection conflict: users reacted to Male and Female; "
              "those changes are ignored until one reaction is removed.")

    # One paternal lineage per person: avoid offering simultaneous, unrelated
    # SNP roles such as J2a + R1b. Even a user who clicks multiple emoji will
    # only receive a lineage when exactly one detailed choice remains.
    dna_choices = {}
    for dna_marker, dna_category, dna_names in menu_groups(by_name):
        if dna_category != "Y-DNA":
            continue
        dna_menu = next((m for m in own_messages if dna_marker in m.get("content", "")), None)
        if not dna_menu:
            continue
        if dna_menu.get("content") != menu_content(dna_marker, dna_category, dna_names):
            continue
        for dna_name, symbol in zip(dna_names, menu_emojis("Y-DNA", dna_names)):
            for uid in react_users(selector["id"], dna_menu["id"], symbol):
                dna_choices.setdefault(uid, set()).add(dna_name)
    dna_conflicts = {uid for uid, choices in dna_choices.items()
                     if len(choices) > 1}
    if dna_conflicts:
        print("[NOTICE] Y-DNA conflicts:", len(dna_conflicts),
              "users chose more than one detailed Y-DNA branch; no new Y-DNA "
              "role will be granted until only one is selected.")

    for marker, category, names in menu_groups(by_name):
        menu = next((m for m in own_messages if marker in m.get("content", "")), None)
        if not menu:
            print("[ACTION REQUIRED] Missing role menu:", marker,
                  ". Run Discord Role Menu & New Results (apply) again.")
            stale_menus += 1
            continue
        if menu.get("content") != menu_content(marker, category, names):
            print("[ACTION REQUIRED] Old role-menu content detected for:", marker,
                  ". Rerun Discord Role Menu & New Results with apply "
                  "to update the message and its emoji mapping.")
            stale_menus += 1
            continue
        reacted = {r.get("emoji", {}).get("name"): int(r.get("count", 0))
                   for r in menu.get("reactions", [])}
        for name, emoji in zip(names, menu_emojis(category, names)):
            # Do not require two reactions (a bot + a human). Existing menu
            # messages can receive a human reaction without a bot seed reaction.
            # We check actual human reactor IDs below.
            if reacted.get(emoji, 0) < 1:
                continue
            if name not in allowed_names:
                raise RuntimeError("A privileged role appeared in menu: " + name)
            selected_role = by_name[name.casefold()]
            role_id = str(selected_role["id"])
            if int(selected_role.get("position", 0)) >= our_position:
                ignored_unmanageable += 1
                print("[ACTION REQUIRED] Cannot assign", name,
                      "- the Egypt YDNA Bot role must be ABOVE this role "
                      "in Discord Server Settings > Roles.", flush=True)
                continue
            # Essential safety: some old origin roles historically had broad
            # Discord permissions. Never allow a reaction to grant any role
            # carrying server-wide powers, especially Administrator/Manage Roles.
            if int(selected_role.get("permissions", "0")) != 0:
                ignored_unmanageable += 1
                print("[SECURITY BLOCK] Cannot assign", name,
                      "- this old origin/DNA role has server-wide permissions. "
                      "The server owner must remove all extra role permissions "
                      "before members can self-select it.", flush=True)
                continue
            for user_id in react_users(selector["id"], menu["id"], emoji):
                examined += 1
                if category == "GENDER" and user_id in gender_conflicts:
                    continue
                if category == "Y-DNA" and user_id in dna_conflicts:
                    continue
                if user_id not in cache:
                    cache[user_id] = api(
                        "GET", f"/guilds/{GID}/members/{user_id}",
                        missing_ok=True)
                data = cache[user_id]
                if not data or data.get("pending"):
                    continue
                known_roles = [str(r) for r in data.get("roles", [])]
                # The server OWNER can operate #choose-roles without the
                # ordinary Verified badge; otherwise require Verified.
                if str(member["id"]) not in known_roles and user_id != str(guild["owner_id"]):
                    ignored_unverified += 1
                    print("[SKIP] User", user_id,
                          "has not received Verified yet; no role granted.")
                    continue
                if role_id in known_roles:
                    continue
                if category == "Y-DNA":
                    other_branches = [r for _, c, entries in menu_groups(by_name)
                                      if c == "Y-DNA" for r in entries if r != name]
                    if any(str(by_name[other.casefold()]["id"]) in known_roles
                           for other in other_branches):
                        print("[SKIP] Member already has another detailed Y-DNA role:",
                              user_id)
                        continue
                if category == "GENDER":
                    other = "Female" if name == "Male" else "Male"
                    other_role = by_name.get(other.casefold())
                    if other_role and str(other_role["id"]) in known_roles:
                        # Refuse ambiguous simultaneous gender roles. Existing
                        # selections can be changed by staff on request.
                        print("SKIP gender choice: an opposite gender role already exists",
                              user_id)
                        continue
                try:
                    api("PUT", f"/guilds/{GID}/members/{user_id}/roles/{role_id}")
                    data.setdefault("roles", []).append(role_id)
                    assigned += 1
                    print(f"Granted self-selected role {name} to user {user_id}")
                except RuntimeError as error:
                    errors += 1
                    print("ERROR assigning self-selected role:", error, file=sys.stderr)
    print("[SUMMARY] human selections checked:", examined,
          "| roles granted:", assigned, "| Discord API errors:", errors,
          "| not Verified:", ignored_unverified,
          "| unsafe/unmanageable roles:", ignored_unmanageable,
          "| outdated/missing menus:", stale_menus, flush=True)
    if not examined:
        print("[CHECK] No eligible human reactions were found. Confirm you "
              "reacted to the actual bot-owned emoji message, not the pinned "
              "overview. Then confirm the GitHub scheduled workflow is enabled.")
    if stale_menus:
        print("[ACTION REQUIRED] Update #choose-roles menu messages with the "
              "Role Menu & New Results apply workflow.")
    if ignored_unmanageable:
        print("[ACTION REQUIRED] Check role positions/permissions. The script "
              "intentionally never grants privileged self-selected roles.")
    if errors:
        raise RuntimeError("Some role assignments failed; check bot's Manage Roles and role order")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, urllib.error.URLError) as exc:
        print("FAILED:", exc, file=sys.stderr)
        sys.exit(1)
