#!/usr/bin/env python3
"""Secure staff role policy and self-service reaction menus for Egypt Y-DNA.

Does not give anyone the Administrator or Manage Roles permissions, except
the bot's existing integration role (left unchanged). The Discord server
OWNER is the only person able to assign Founder/Administrator/Moderator.
All other roles may be self-selected in #choose-roles only after Member gate.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from discord_server_redesign import ORIGIN, HAPLOS

GID = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
MODE = os.getenv("MODE", "preview").strip()
BASE = "https://discord.com/api/v10"

ADMINISTRATOR = 1 << 3
MANAGE_ROLES = 1 << 28
CREATE_INVITE = 1 << 0
KICK = 1 << 1
BAN = 1 << 2
MANAGE_CHANNELS = 1 << 4
MANAGE_GUILD = 1 << 5
ADD_REACTIONS = 1 << 6
VIEW_AUDIT_LOG = 1 << 7
VIEW = 1 << 10
SEND = 1 << 11
READ_HISTORY = 1 << 16
MANAGE_MESSAGES = 1 << 13
MANAGE_NICKNAMES = 1 << 27
MANAGE_THREADS = 1 << 34
MANAGE_EVENTS = 1 << 33
MANAGE_WEBHOOKS = 1 << 29
MANAGE_GUILD_EXPRESSIONS = 1 << 30
MODERATE_MEMBERS = 1 << 40

# These deliberately exclude both ADMINISTRATOR and MANAGE_ROLES.
POLICY = {
    "Founder": (MANAGE_GUILD | MANAGE_CHANNELS | MANAGE_EVENTS |
                MANAGE_WEBHOOKS | MANAGE_GUILD_EXPRESSIONS |
                BAN | KICK | MANAGE_MESSAGES | MANAGE_THREADS |
                MODERATE_MEMBERS | VIEW_AUDIT_LOG | MANAGE_NICKNAMES),
    "Administrator": (MANAGE_GUILD | MANAGE_CHANNELS | MANAGE_EVENTS |
                      BAN | KICK | MANAGE_MESSAGES | MANAGE_THREADS |
                      MODERATE_MEMBERS | VIEW_AUDIT_LOG | MANAGE_NICKNAMES),
    "Moderator": (KICK | MANAGE_MESSAGES | MANAGE_THREADS |
                  MODERATE_MEMBERS | VIEW_AUDIT_LOG | MANAGE_NICKNAMES),
}
STAFF = ("Founder", "Administrator", "Moderator")
LEGACY_ORIGINS = ("Copt", "Amazighi", "Central Asian", "European",
                  "South Asian", "East Asian", "Sea Asians", "Native")
EMOJIS = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
          "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")
PER_CHUNK = len(EMOJIS)
ROLE_MARKER = "**EGYPT Y-DNA ROLE SELECTION:"

def api(method, path, data=None):
    raw = json.dumps(data).encode() if data is not None else None
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + path, data=raw, method=method,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNAStaff/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                content = res.read()
                time.sleep(0.16)
                return json.loads(content) if content else None
        except urllib.error.HTTPError as ex:
            body = ex.read().decode(errors="replace")
            if ex.code == 429 and attempt < 5:
                try: delay = min(30, float(json.loads(body).get("retry_after", 2)))
                except (ValueError, TypeError): delay = 2
                time.sleep(delay + 0.4)
                continue
            raise RuntimeError(f"Discord HTTP {ex.code} {method} {path}: {body[:450]}")
    raise RuntimeError("Rate limit retries exhausted")

def maybe(method, path, payload, label):
    if MODE == "preview":
        print("[PREVIEW]", label, flush=True)
        return None
    data = api(method, path, payload)
    print("[APPLIED]", label, flush=True)
    return data

def menu_groups(role_by_name):
    groups = []
    for category, choices in (
        ("ORIGIN", list(ORIGIN) + list(LEGACY_ORIGINS)),
        ("Y-DNA", list(HAPLOS))
    ):
        available = [name for name in dict.fromkeys(choices)
                     if name.casefold() in role_by_name]
        for offset in range(0, len(available), PER_CHUNK):
            chunk = available[offset:offset+PER_CHUNK]
            group_no = offset // PER_CHUNK + 1
            marker = f"{ROLE_MARKER} {category} {group_no}**"
            groups.append((marker, category, chunk))
    return groups

def menu_content(marker, category, names):
    intro = ("**Choose your geographical/heritage origins** (self-declared, optional)"
             if category == "ORIGIN" else
             "**Choose your Y-DNA haplogroup** (self-reported, NOT verified)")
    lines = [marker, intro,
             "React with the matching number(s). Each selection grants one role.",
             "You can choose more than one. No staff or verified-tester roles are available.",
             ""]
    lines += [f"{EMOJIS[i]} {name}" for i, name in enumerate(names)]
    lines.append("\nRole changes are processed periodically; ask a moderator to remove a selection.")
    return "\n".join(lines)

def members_only_overwrites(member_id, bot_id, staff_ids):
    result = [
        {"id": GID, "type": 0, "allow": "0", "deny": str(VIEW | SEND)},
        {"id": member_id, "type": 0,
         "allow": str(VIEW | READ_HISTORY | ADD_REACTIONS), "deny": str(SEND)},
    ]
    for role_id in staff_ids:
        result.append({"id": role_id, "type": 0,
                       "allow": str(VIEW | SEND | READ_HISTORY | ADD_REACTIONS),
                       "deny": "0"})
    result.append({"id": bot_id, "type": 1,
                   "allow": str(VIEW | SEND | READ_HISTORY | ADD_REACTIONS),
                   "deny": "0"})
    return result

def main():
    if MODE not in ("preview", "apply"):
        raise ValueError("MODE must be preview or apply")
    if not GID.isdecimal() or not TOKEN:
        raise ValueError("Missing GitHub Secrets DISCORD_GUILD_ID / DISCORD_BOT_TOKEN")

    guild = api("GET", f"/guilds/{GID}")
    bot = api("GET", "/users/@me")
    roles = api("GET", f"/guilds/{GID}/roles")
    by_name = {role["name"].casefold(): role for role in roles}
    staff = {}
    print("Server:", guild["name"], "mode:", MODE, "owner_id:", guild["owner_id"])
    for name in STAFF:
        role = by_name.get(name.casefold())
        if not role:
            raise RuntimeError("Missing " + name + " role. Run server setup first.")
        staff[name] = role
    member = by_name.get("member")
    if not member:
        raise RuntimeError("Missing Member role; run Discord server setup first.")

    # SAFETY PREFLIGHT: Check all role edits before performing any writes.
    # A bot cannot edit a role at or above its top role. It also cannot grant
    # permission flags it does not itself have (Discord role hierarchy rules).
    bot_member = api("GET", f"/guilds/{GID}/members/{bot['id']}")
    by_id = {str(r["id"]): r for r in roles}
    bot_assigned_ids = {str(GID)} | {str(i) for i in bot_member.get("roles", [])}
    bot_top = max((int(by_id[i]["position"]) for i in bot_assigned_ids
                   if i in by_id), default=-1)
    bot_permissions = 0
    for rid in bot_assigned_ids:
        if rid in by_id:
            bot_permissions |= int(by_id[rid].get("permissions", "0"))
    if bot_permissions & ADMINISTRATOR:
        bot_permissions = (1 << 63) - 1

    permission_names = (
        (KICK, "Kick Members"), (BAN, "Ban Members"),
        (MANAGE_CHANNELS, "Manage Channels"),
        (MANAGE_GUILD, "Manage Server"),
        (VIEW_AUDIT_LOG, "View Audit Log"),
        (MANAGE_MESSAGES, "Manage Messages"),
        (MANAGE_NICKNAMES, "Manage Nicknames"),
        (MANAGE_EVENTS, "Manage Events"),
        (MANAGE_WEBHOOKS, "Manage Webhooks"),
        (MANAGE_GUILD_EXPRESSIONS, "Manage Expressions"),
        (MANAGE_THREADS, "Manage Threads"),
        (MODERATE_MEMBERS, "Timeout Members"),
        (MANAGE_ROLES, "Manage Roles"),
    )
    def human_permissions(bits):
        matched = [label for flag, label in permission_names if bits & flag]
        return ", ".join(matched) if matched else "(none)"

    print("[PREFLIGHT] Bot highest role position:", bot_top, flush=True)
    print("[PREFLIGHT] Bot can manage roles:",
          bool(bot_permissions & MANAGE_ROLES), flush=True)

    ordinary = {n.casefold() for n in
        list(ORIGIN) + list(HAPLOS) + list(LEGACY_ORIGINS) +
        ["Member", "Research Contributor", "Verified Y-DNA Tester",
         "Contributor", "Verified Tester"]}
    planned = []
    hierarchy_problems = []
    insufficient_flags = 0
    for role in roles:
        if role.get("managed") or str(role["id"]) == GID:
            # @everyone is a server baseline; never rewrite it implicitly.
            continue
        name = role["name"]
        current = int(role.get("permissions", "0"))
        if name in POLICY:
            desired = POLICY[name]
        elif name.casefold() in ordinary:
            desired = 0
        else:
            desired = current & ~(ADMINISTRATOR | MANAGE_ROLES)
        if current == desired:
            continue
        planned.append((role, current, desired))
        if int(role["position"]) >= bot_top:
            hierarchy_problems.append(f"{name} (position {role['position']})")
        missing = desired & ~bot_permissions
        if missing:
            insufficient_flags |= missing
            print("[PREFLIGHT] Cannot grant to", name, ":",
                  human_permissions(missing), flush=True)

    print("[PREFLIGHT] Role updates pending:", len(planned), flush=True)
    problems = []
    if planned and not (bot_permissions & MANAGE_ROLES):
        problems.append(
            "Bot lacks Manage Roles. In Discord: Server Settings > Roles > "
            "Egypt YDNA Bot > Permissions > Manage Roles.")
    if hierarchy_problems:
        problems.append(
            "Bot role must be HIGHER than these roles: " +
            "; ".join(hierarchy_problems[:12]) +
            (f" (and {len(hierarchy_problems)-12} more)" if len(hierarchy_problems) > 12 else ""))
    if insufficient_flags:
        problems.append(
            "Bot cannot grant these staff permissions: " +
            human_permissions(insufficient_flags) +
            ". Temporarily grant them to Egypt YDNA Bot in Server Settings > "
            "Roles > Egypt YDNA Bot > Permissions. After applying, you may "
            "remove unnecessary powers from the bot, but KEEP Manage Roles "
            "for ongoing member verification and self-selected roles.")
    if bot_top < 4:
        problems.append(
            "The bot role is too low for Founder > Administrator > Moderator. "
            "Move Egypt YDNA Bot to the top of the role list.")
    if problems:
        for item in problems:
            print("[ACTION REQUIRED]", item, flush=True)
        if MODE == "apply":
            raise RuntimeError(
                "Discord role permission preflight failed. Fix the [ACTION REQUIRED] "
                "items above, then run a NEW apply. No role/channel edits were "
                "attempted by this run.")
        print("[PREVIEW] No changes will be made until the listed problems are fixed.")
    elif MODE == "preview":
        print("[PREVIEW] Role permission preflight passed.")

    # Only edit roles after we know the requested staff permissions can be set.
    for role, current, desired in planned:
        maybe("PATCH", f"/guilds/{GID}/roles/{role['id']}",
              {"permissions": str(desired)},
              f"set permissions for {role['name']}: {current} -> {desired}")

    # Ensure role hierarchy: bot above Founder > Administrator > Moderator.
    desired = {name: bot_top - (i+1) for i, name in enumerate(STAFF)}
    # Explicitly reorder staff roles below bot, above all other custom roles.
    # This operation never reorders the bot's own managed role.
    if any(int(staff[name]["position"]) != desired[name] for name in STAFF):
        maybe("PATCH", f"/guilds/{GID}/roles",
              [{"id": str(staff[name]["id"]), "position": desired[name]}
               for name in STAFF],
              "order roles: Bot > Founder > Administrator > Moderator > members")
    else:
        print("[OK] Staff hierarchy already correct")

    # Founder member count: Discord has NO built-in max-role-usage setting.
    # Report violations; only owner can hand out a second Founder role.
    try:
        counts = api("GET", f"/guilds/{GID}/roles/member-counts")
        n_founders = int(counts.get(str(staff["Founder"]["id"]), 0))
        print(f"[CHECK] Founder has {n_founders} members (policy max: 2)")
        if n_founders > 2:
            print("[WARNING] MORE THAN TWO FOUNDERS: owner must remove extras.")
    except RuntimeError as ex:
        print("[NOTICE] Founder count could not be checked:", ex)

    channel_list = api("GET", f"/guilds/{GID}/channels")
    # Give all staff the ability to see/manage member-gated channels even
    # when they have not separately taken the ordinary Member role.
    staff_ids = [str(staff[n]["id"]) for n in STAFF]
    staff_category = next((c for c in channel_list if c["type"] == 4 and
                           c["name"] in ("🔒 STAFF", "🔒 STAFF ONLY")), None)
    forbidden = {"id": GID, "type": 0, "allow": "0",
                 "deny": str(VIEW | SEND)}
    bot_rule = {"id": str(bot["id"]), "type": 1,
                "allow": str(VIEW | SEND | READ_HISTORY), "deny": "0"}
    for ch in channel_list:
        is_staff = (staff_category is not None and
                    (str(ch["id"]) == str(staff_category["id"]) or
                     str(ch.get("parent_id")) == str(staff_category["id"])))
        if is_staff:
            overrides = [forbidden] + [
                {"id": rid, "type": 0,
                 "allow": str(VIEW | SEND | READ_HISTORY), "deny": "0"}
                for rid in staff_ids] + [bot_rule]
        elif ch["type"] in (0, 2, 4, 15):
            # Keep other permission overwrites unchanged; only ensure staff
            # can view/read/send in channels shared with the community.
            overrides = [dict(o) for o in ch.get("permission_overwrites", [])]
            for rid in staff_ids:
                old = next((o for o in overrides if str(o["id"]) == rid and
                            o["type"] == 0), None)
                if old is None:
                    old = {"id": rid, "type": 0, "allow": "0", "deny": "0"}
                    overrides.append(old)
                bits = VIEW | SEND | READ_HISTORY
                old["allow"] = str(int(old.get("allow", "0")) | bits)
                old["deny"] = str(int(old.get("deny", "0")) & ~bits)
        else:
            continue
        if overrides != ch.get("permission_overwrites", []):
            maybe("PATCH", "/channels/" + str(ch["id"]),
                  {"permission_overwrites": overrides},
                  ("secure private STAFF access: " if is_staff else
                   "allow staff in ordinary channel: ") + ch["name"])

    chosen_category = next((c for c in channel_list if c["type"] == 4 and
        c["name"] in ("📌 START HERE", "📌 INFORMATION")), None)
    choose = next((c for c in channel_list if c["type"] == 0 and
                   c["name"] == "choose-roles"), None)
    perms = members_only_overwrites(str(member["id"]), str(bot["id"]),
                                  [str(staff[n]["id"]) for n in STAFF])
    if not choose:
        payload = {"name": "choose-roles", "type": 0,
                   "topic": "Choose your own origin and Y-DNA roles (after verification).",
                   "permission_overwrites": perms}
        if chosen_category:
            payload["parent_id"] = chosen_category["id"]
        choose = maybe("POST", f"/guilds/{GID}/channels", payload,
                       "create protected #choose-roles")
    elif choose.get("permission_overwrites", []) != perms:
        payload = {"permission_overwrites": perms}
        if chosen_category and str(choose.get("parent_id")) != str(chosen_category["id"]):
            payload["parent_id"] = str(chosen_category["id"])
        maybe("PATCH", "/channels/" + str(choose["id"]), payload,
              "restrict #choose-roles to Member + staff")
    if not choose:
        if MODE == "preview":
            print("[PREVIEW] Prepare numbered role-selection posts")
            for marker, category, choices in menu_groups(by_name):
                print("[PREVIEW]", marker, "::", ", ".join(choices))
        return

    messages = api("GET", f"/channels/{choose['id']}/messages?limit=100")
    mine = [m for m in messages if str(m.get("author", {}).get("id")) == str(bot["id"])]
    for marker, category, names in menu_groups(by_name):
        content = menu_content(marker, category, names)
        target = next((m for m in mine if marker in m.get("content", "")), None)
        if target:
            if target.get("content") != content:
                maybe("PATCH", f"/channels/{choose['id']}/messages/{target['id']}",
                      {"content": content, "allowed_mentions": {"parse": []}},
                      "refresh role selection " + marker)
        else:
            target = maybe("POST", f"/channels/{choose['id']}/messages",
                           {"content": content, "allowed_mentions": {"parse": []}},
                           "post " + marker)
        if target:
            already = {r.get("emoji", {}).get("name") for r in target.get("reactions", [])}
            for symbol in EMOJIS[:len(names)]:
                if symbol not in already:
                    maybe("PUT",
                          f"/channels/{choose['id']}/messages/{target['id']}"
                          f"/reactions/{urllib.parse.quote(symbol, safe='')}/@me",
                          None, "react " + symbol + " on " + marker)
    print("DONE: No staff roles are offered for self-selection.")
    print("The scheduled role selector must process reactions to assign roles.")
    print("Only the server owner may assign Founder/Administrator/Moderator roles.")
    print("Discord does not natively hard-cap the Founder role to two members.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as exc:
        print("FAILED:", exc, file=sys.stderr, flush=True)
        sys.exit(1)
