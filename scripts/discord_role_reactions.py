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
    roles = api("GET", f"/guilds/{GID}/roles")
    by_name = {r["name"].casefold(): r for r in roles}
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
    bot = api("GET", "/users/@me")
    messages = api("GET", f"/channels/{selector['id']}/messages?limit=100")
    own_messages = [m for m in messages or [] if
                    str(m.get("author", {}).get("id")) == str(bot["id"])]
    cache = {}
    examined = assigned = errors = 0
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

    for marker, category, names in menu_groups(by_name):
        menu = next((m for m in own_messages if marker in m.get("content", "")), None)
        if not menu:
            print("NOTICE: Missing menu:", marker)
            continue
        if menu.get("content") != menu_content(marker, category, names):
            print("NOTICE: Out-of-date menu, skipping:", marker)
            continue
        reacted = {r.get("emoji", {}).get("name"): int(r.get("count", 0))
                   for r in menu.get("reactions", [])}
        for name, emoji in zip(names, menu_emojis(category, names)):
            # Bot adds one reaction of its own to each choice.
            if reacted.get(emoji, 0) < 2:
                continue
            if name not in allowed_names:
                raise RuntimeError("A privileged role appeared in menu: " + name)
            role_id = str(by_name[name.casefold()]["id"])
            for user_id in react_users(selector["id"], menu["id"], emoji):
                examined += 1
                if category == "GENDER" and user_id in gender_conflicts:
                    continue
                if user_id not in cache:
                    cache[user_id] = api(
                        "GET", f"/guilds/{GID}/members/{user_id}",
                        missing_ok=True)
                data = cache[user_id]
                if not data or data.get("pending"):
                    continue
                known_roles = [str(r) for r in data.get("roles", [])]
                if str(member["id"]) not in known_roles:
                    continue  # Must first accept the rules.
                if role_id in known_roles:
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
    print(f"DONE: selections checked={examined}, roles granted={assigned}, errors={errors}")
    if errors:
        raise RuntimeError("Some role assignments failed; check bot's Manage Roles and role order")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, urllib.error.URLError) as exc:
        print("FAILED:", exc, file=sys.stderr)
        sys.exit(1)
