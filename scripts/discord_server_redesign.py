#!/usr/bin/env python3
"""Egypt Y-DNA Discord redesign. Preview-only by default, no deletions.

Existing categories/channels are renamed or moved only where explicitly
mapped below. New members receive Member automatically after a ✅ reaction in #verification.
Scheduled GitHub Actions checks confirmations approximately every 5 minutes.
"""
import json, os, sys, time, urllib.error, urllib.request

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
MODE = os.getenv("MODE", "preview").strip()
BASE = "https://discord.com/api/v10"
INVITE = 1 << 0
VIEW = 1 << 10
SEND = 1 << 11
ADD_REACTIONS = 1 << 6
READ_HISTORY = 1 << 16
THREAD_SEND = 1 << 38

STAFF = ["Administrator", "Moderator"]
CORE = ["Founder", "Administrator", "Moderator", "Member",
        "Research Contributor", "Verified Y-DNA Tester"]
# This is one combined, self-reported geographical-origin group.
# Regions refer to geography, NOT genetic/ethnic classifications.
ORIGIN = [
    "North Africa", "West Africa", "Central Africa", "East Africa", "Southern Africa",
    "Egypt", "Maghreb", "Nile Valley / Nubia", "Horn of Africa",
    "Northern Europe", "Western Europe", "Southern Europe", "Balkans", "Eastern Europe",
    "West Asia", "Levant", "Arabian Peninsula", "Mesopotamia", "Anatolia", "Caucasus",
    "Iranian Plateau", "North Asia", "Central Asia", "South Asia", "East Asia", "Southeast Asia",
    "North America", "Central America", "Caribbean", "South America",
    "Australia & New Zealand", "Melanesia", "Micronesia", "Polynesia",
    "Indigenous Peoples", "Multiple Regions", "Prefer Not to Say",
]
# User-selectable confirmed/predicted Y-DNA affiliation, not auto-verified.
HAPLOS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L",
    "M", "N", "O", "P", "Q", "R", "S", "T",
    "E-M2", "E-M35", "E-M78", "E-M81", "E-M123", "E-V13", "E-V22", "E-V32",
    "J1", "J1-P58", "J2", "J2a", "J2b",
    "R1a", "R1b", "R1b-V88", "R1b-M269", "R2",
    "Q1", "Q2", "T-M70", "T-P77", "G1", "G2", "I1", "I2",
    "L1", "L2", "H1", "H2", "Not tested", "Other / unresolved",
]
ROLE_ALIASES = {
    "Research Contributor": ["Contributor"],
    "Verified Y-DNA Tester": ["Verified Tester"],
}
ORIGIN_ROLE_COLORS = {
    "North Africa": 0x29D229,
    "West Africa": 0x2929D2,
    "Central Africa": 0x49D68F,
    "East Africa": 0xD22953,
    "Southern Africa": 0xBDD229,
    "Egypt": 0xC89A2B,
    "Maghreb": 0xD229D2,
    "Nile Valley / Nubia": 0x598430,
    "Horn of Africa": 0x498FD6,
    "Northern Europe": 0x49D6D6,
    "Western Europe": 0x843045,
    "Southern Europe": 0xD25329,
    "Balkans": 0x7754BB,
    "Eastern Europe": 0x80CB53,
    "West Asia": 0x304F84,
    "Levant": 0x3C1E96,
    "Arabian Peninsula": 0xB4C05F,
    "Mesopotamia": 0x49B3D6,
    "Anatolia": 0xD2297E,
    "Caucasus": 0x8F49D6,
    "Iranian Plateau": 0x961E1E,
    "North Asia": 0x846F30,
    "Central Asia": 0xC05F84,
    "South Asia": 0x1E9659,
    "East Asia": 0x5FC09B,
    "Southeast Asia": 0xD229A8,
    "North America": 0x1E961E,
    "Central America": 0x871E96,
    "Caribbean": 0x2953D2,
    "South America": 0xD27E29,
    "Australia & New Zealand": 0xD2BD29,
    "Melanesia": 0x1E7896,
    "Micronesia": 0xC05F5F,
    "Polynesia": 0x8D8D26,
    "Indigenous Peoples": 0x366CC5,
    "Multiple Regions": 0xAB459A,
    "Prefer Not to Say": 0x6D7886,
    "Copt": 0xAD613A,
    "Amazighi": 0x218C79,
    "Central Asian": 0x303084,
    "European": 0xC08F5F,
    "South Asian": 0x29D268,
    "East Asian": 0xBC53CB,
    "Sea Asians": 0x93D229,
    "Native": 0x843064,
}

def role_color(name, group):
    if name == "Founder": return 0xD4AF37
    if name == "Administrator": return 0xC0392B
    if name == "Moderator": return 0x2980B9
    if name == "Member": return 0x95A5A6
    if name == "Research Contributor": return 0x00A6A6
    if name == "Verified Y-DNA Tester": return 0x27AE60
    if group == "origin": return ORIGIN_ROLE_COLORS[name]
    if group == "haplo":
        prefixes = [
            ("J1", 0x218C53), ("J2", 0x7AAE48), ("E", 0x2563A6),
            ("R1b", 0xBB4040), ("R1a", 0xB58A63), ("R2", 0xB59C27),
            ("Q", 0x845EC2), ("T", 0xCF7D28), ("L", 0x3CA6B0),
            ("G", 0x808080), ("I", 0x8D74AE)
        ]
        for prefix, color in prefixes:
            if name == prefix or name.startswith(prefix + "-"):
                return color
    return 0x7F8C8D

ROLES = [(n, "staff") for n in CORE[:3]] + [
    (n, "member") for n in CORE[3:]
] + [(n, "origin") for n in ORIGIN] + [(n, "haplo") for n in HAPLOS]

# (target name, kind, permission mode, information/description)
DESIGN = [
    ("📌 START HERE", [
        ("welcome", 0, "public", "Welcome to the Egypt Y-DNA community."),
        ("rules", 0, "public", "Read the community rules before verification."),
        ("verification", 0, "verify", "React with ✅ to confirm the rules and unlock the server."),
        ("announcements", 0, "read", "Official announcements."),
        ("server-guide", 0, "read", "How to participate and submit a Y-DNA result."),
    ]),
    ("🧬 Y-DNA RESEARCH", [
        ("new-results", 0, "read", "Source-checked Egyptian Y-DNA results."),
        ("submit-results", 15, "members", "Submit publicly documented Y-DNA results for review."),
        ("haplogroup-discussion", 15, "members", "Discuss confirmed SNP branches, STR predictions and phylogenetic trees."),
        ("ancient-dna", 15, "members", "Scientific discussions of ancient DNA."),
    ]),
    ("🌍 COMMUNITY", [
        ("english-chat", 0, "members", "Main community chat — English."),
        ("arabic-chat", 0, "members", "نقاش عام باللغة العربية"),
        ("introductions", 0, "members", "Introduce yourself without sharing private details."),
    ]),
    ("🗺️ RESOURCES", [
        ("egyptian-governorates", 0, "members", "Discuss publicly documented regional sample origins."),
        ("project-map", 0, "read", "Egypt Y-DNA map and public archive."),
        ("useful-links", 0, "read", "Reliable external research resources."),
    ]),
    ("🔒 STAFF", [
        ("mod-log", 0, "staff", "Staff-only moderation notes (not an automatic event log)."),
        ("member-review", 0, "staff", "Staff-only membership approval and role assignments."),
        ("staff-chat", 0, "staff", "Private staff coordination."),
    ]),
]
# Rename previous installer labels, retaining Discord channel IDs and message history.
CATEGORY_ALIASES = {
    "📌 START HERE": ["📌 INFORMATION"],
    "🧬 Y-DNA RESEARCH": ["🧬 Y-DNA RESULTS"],
    "🌍 COMMUNITY": ["💬 COMMUNITY"],
    "🗺️ RESOURCES": ["🗺️ EGYPTIAN ORIGINS"],
    "🔒 STAFF": ["🔒 STAFF ONLY"],
}
CHANNEL_ALIASES = {
    "server-guide": ["how-to-submit"],
    "egyptian-governorates": ["governorates"],
    "project-map": ["ydna-map"],
    "mod-log": ["moderation"],
}
RULES = (
    "📜 **EGYPT Y-DNA — COMMUNITY RULES**\n"
    "1. **Respect everyone.** No insults, harassment, hate, discrimination, or personal attacks.\n"
    "2. **Keep discussions factual.** Cite sources; separate evidence from speculation.\n"
    "3. **Stay on topic.** This server focuses on Egyptian Y-DNA and genetic genealogy.\n"
    "4. **No religious or political debates.** Historical context is welcome when relevant and sourced.\n"
    "5. **No NSFW, graphic, offensive material, scams, or spam.**\n"
    "6. **Protect DNA privacy.** Do not disclose private results, kit numbers, personal names or precise locations without permission.\n"
    "7. **English is the primary language.** Arabic is welcome in #arabic-chat.\n"
    "8. **Be careful with ancestry claims.** Regional roles are self-declared, not genetic proof; SNPs may be confirmed or predicted.\n"
    "9. **Follow moderators' instructions.** Repeat violations may result in restrictions or removal.\n"
    "To unlock the server, read these rules and react with ✅ in #verification."
)
MESSAGES = {
    "welcome": "🧬 **Welcome to Egypt Y-DNA!**\nInternational Egyptian Y-DNA research and genetic genealogy community.\nMain chat: #english-chat | Arabic: #arabic-chat\nProject: https://egyptydna.github.io/Egypt-Y-DNA/\nPlease read #rules and react with ✅ in #verification. Your Member role will be assigned automatically in a few minutes.",
    "rules": RULES,
    "verification": "✅ **EGYPT Y-DNA VERIFICATION**\nPlease read #rules carefully. By reacting with ✅ below, you confirm that you have read and agree to the rules. Once processed, the Member role is assigned and the other channels become visible. This check runs approximately every five minutes; it can be delayed.\nNo DNA test or personal information is required.",
    "server-guide": "📖 **Getting started**\nJoin the main discussions in #english-chat. Share one sourced result per post in #submit-results; note your terminal confirmed SNP, testing platform, source, and Egyptian governorate if publicly documented or consented. Do not upload private DNA files.\nChoose any applicable geographical-origin and Y-DNA roles (self-declared); these never prove ancestry. The Member role is assigned automatically after you confirm #rules in #verification.",
    "new-results": "🆕 **Confirmed Egyptian Y-DNA results**\nStaff will post reviewed samples with sources. An unverified submission is not a confirmed new result.\nhttps://egyptydna.github.io/Egypt-Y-DNA/",
    "project-map": "🗺️ **Egypt Y-DNA Project**\nhttps://egyptydna.github.io/Egypt-Y-DNA/\nLocations are approximate at the governorate level.",
    "useful-links": "🔗 **Research resources**\nYFull: https://www.yfull.com/tree/\nFTDNA Discover: https://discover.familytreedna.com/\nISOGG: https://isogg.org/\nEgyptian Y-DNA Project: https://egyptydna.github.io/Egypt-Y-DNA/",
}

def request(method, path, data=None):
    payload = None if data is None else json.dumps(data).encode()
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + path, method=method, data=payload,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNARedesign/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as reply:
                contents = reply.read()
                time.sleep(0.3)
                return json.loads(contents) if contents else None
        except urllib.error.HTTPError as error:
            message = error.read().decode(errors="replace")
            if error.code == 429 and attempt < 5:
                try:
                    pause = min(30, float(json.loads(message).get("retry_after", 2)))
                except (TypeError, ValueError):
                    pause = 2
                time.sleep(pause + 0.5)
                continue
            raise RuntimeError(f"{method} {path}: HTTP {error.code}: {message[:350]}")
    raise RuntimeError("Discord rate limit retries exhausted")

def change(method, path, data, what):
    if MODE == "preview":
        print("[PREVIEW]", what)
        return None
    result = request(method, path, data)
    print("[APPLIED]", what)
    return result

def entry(role_id, allow=0, deny=0, kind=0):
    return {"id": str(role_id), "type": kind,
            "allow": str(allow), "deny": str(deny)}

def overlays(channel, access, member_id, staff_ids, bot_id, kind):
    """Explicitly hide member-only channels until the Member role is granted."""
    prior = channel.get("permission_overwrites", []) if channel else []
    overwrites = {(str(o["id"]), o["type"]): dict(o) for o in prior}
    def set_permission(id, kind_, allow, deny):
        key = (str(id), kind_)
        old = overwrites.get(key, entry(id, kind=kind_))
        old_allow, old_deny = int(old["allow"]), int(old["deny"])
        involved = allow | deny
        old["allow"] = str((old_allow & ~involved) | allow)
        old["deny"] = str((old_deny & ~involved) | deny)
        overwrites[key] = old
    if access == "staff":
        set_permission(GUILD, 0, 0, VIEW | SEND | THREAD_SEND)
        set_permission(member_id, 0, 0, VIEW | SEND | THREAD_SEND)
        for id in staff_ids:
            set_permission(id, 0, VIEW | SEND | THREAD_SEND | READ_HISTORY, 0)
    elif access == "public":
        set_permission(GUILD, 0, VIEW | READ_HISTORY, SEND | THREAD_SEND)
        set_permission(member_id, 0, VIEW | READ_HISTORY, SEND | THREAD_SEND)
        for id in staff_ids:
            set_permission(id, 0, VIEW | SEND | READ_HISTORY, 0)
    elif access == "verify":
        set_permission(GUILD, 0, VIEW | READ_HISTORY | ADD_REACTIONS, SEND | THREAD_SEND)
        set_permission(member_id, 0, VIEW | READ_HISTORY | ADD_REACTIONS, SEND | THREAD_SEND)
        for id in staff_ids:
            set_permission(id, 0, VIEW | SEND | READ_HISTORY | ADD_REACTIONS, 0)
    elif access == "read":
        set_permission(GUILD, 0, 0, VIEW | SEND | THREAD_SEND)
        set_permission(member_id, 0, VIEW | READ_HISTORY, SEND | THREAD_SEND)
        for id in staff_ids:
            set_permission(id, 0, VIEW | SEND | READ_HISTORY, 0)
    elif access == "members":
        set_permission(GUILD, 0, 0, VIEW | SEND | THREAD_SEND)
        set_permission(member_id, 0, VIEW | SEND | THREAD_SEND | READ_HISTORY, 0)
        for id in staff_ids:
            set_permission(id, 0, VIEW | SEND | READ_HISTORY, 0)
    set_permission(bot_id, 1, VIEW | SEND | THREAD_SEND | READ_HISTORY | ADD_REACTIONS, 0)
    return list(overwrites.values())


def find_channel(channels, name, kind, aliases=()):
    matches = [c for c in channels
               if c["type"] == kind and c["name"].casefold() == name.casefold()]
    if matches:
        return matches[0], False
    for alias in aliases:
        candidates = [c for c in channels
                      if c["type"] == kind and c["name"].casefold() == alias.casefold()]
        if candidates:
            return candidates[0], True
    return None, False

def main():
    if MODE not in ("preview", "apply", "colors-preview", "colors-apply"):
        raise ValueError("MODE must be preview, apply, colors-preview or colors-apply")
    if not TOKEN or not GUILD.isdecimal():
        raise ValueError("GitHub secrets DISCORD_BOT_TOKEN and DISCORD_GUILD_ID required")
    guild = request("GET", "/guilds/" + GUILD)
    bot = request("GET", "/users/@me")
    print("Server:", guild["name"], "| mode:", MODE, "| bot:", bot["username"])
    community = "COMMUNITY" in guild.get("features", [])
    existing_roles = request("GET", "/guilds/" + GUILD + "/roles")
    existing_by_name = {r["name"].casefold(): r for r in existing_roles}

    # Dedicated, safe recoloring command. This never creates/deletes/renames
    # roles, changes permissions, or modifies channels. It also bypasses
    # unrelated setup checks so a channel issue cannot block role colors.
    if MODE in ("colors-preview", "colors-apply"):
        issues = []
        recolored = 0
        unchanged = 0
        missing = 0
        values = list(ORIGIN_ROLE_COLORS.values())
        if len(values) != len(set(values)):
            raise RuntimeError("Origin role palette contains repeated colors")
        for name, color in ORIGIN_ROLE_COLORS.items():
            old = existing_by_name.get(name.casefold())
            if not old:
                print("[MISSING] origin role:", name, "(not created by colors mode)")
                missing += 1
                continue
            current = int(old.get("color", 0))
            if current == color:
                print(f"[OK] {name}: #{color:06X}")
                unchanged += 1
                continue
            description = f"recolor {name}: #{current:06X} -> #{color:06X}"
            if MODE == "colors-preview":
                print("[PREVIEW]", description)
            else:
                try:
                    change("PATCH", f"/guilds/{GUILD}/roles/{old['id']}",
                           {"color": color}, description)
                    recolored += 1
                except RuntimeError as error:
                    issues.append(name)
                    print("[FAILED]", description, str(error), flush=True)
        print(f"Origin palette: {len(values)} unique colors; "
              f"{unchanged} already correct, {recolored} updated, "
              f"{missing} roles not present, {len(issues)} errors.")
        if MODE == "colors-preview":
            print("Read-only preview. Use colors-apply to change ONLY colors.")
        if issues:
            raise RuntimeError("Could not recolor these roles: " + ", ".join(issues))
        return

    role_ids = {}
    print("\n== SELF-SELECTABLE ROLES / NO SPECIAL PERMISSIONS ==")
    for name, group in ROLES:
        old = existing_by_name.get(name.casefold())
        alias = False
        if not old:
            for alternate in ROLE_ALIASES.get(name, []):
                old = existing_by_name.get(alternate.casefold())
                if old:
                    alias = True
                    break
        if old:
            role_ids[name] = str(old["id"])
            changes = {}
            if alias:
                changes["name"] = name
            if group in ("origin", "haplo") and int(old["permissions"]) != 0:
                changes["permissions"] = "0"
            if group == "origin" and int(old.get("color", 0)) != role_color(name, group):
                changes["color"] = role_color(name, group)
            if changes:
                try:
                    change("PATCH", "/guilds/" + GUILD + "/roles/" + str(old["id"]),
                           changes, "align existing role: " + str(old["name"]) + " -> " + name)
                except RuntimeError as exc:
                    print("[NOTICE] Existing role is protected by hierarchy; change manually:", exc)
            else:
                print("[EXISTS]", group, "role:", name)
        else:
            created = change("POST", "/guilds/" + GUILD + "/roles",
                  {"name": name, "permissions": "0", "mentionable": False,
                   "color": role_color(name, group), "hoist": False},
                  f"create neutral {group} role: {name}")
            if created:
                role_ids[name] = str(created["id"])
    # Recolor pre-existing origin/identity roles without changing names,
    # assigned members, hierarchy or their existing permissions.
    for old_name in ["Copt","Amazighi","Central Asian","European","South Asian","East Asian","Sea Asians","Native"]:
        old = existing_by_name.get(old_name.casefold())
        if old and int(old.get("color", 0)) != ORIGIN_ROLE_COLORS[old_name]:
            try:
                change("PATCH", "/guilds/" + GUILD + "/roles/" + str(old["id"]),
                       {"color": ORIGIN_ROLE_COLORS[old_name]},
                       "recolor existing origin role: " + old_name)
            except RuntimeError as exc:
                print("[NOTICE] Could not recolor existing origin role:", old_name, exc)
    everyone = next((r for r in existing_roles if str(r["id"]) == GUILD), None)
    if everyone and not (int(everyone["permissions"]) & INVITE):
        try:
            change("PATCH", f"/guilds/{GUILD}/roles/{GUILD}",
                   {"permissions": str(int(everyone["permissions"]) | INVITE)},
                   "permit all members to create server invitations")
        except RuntimeError as exc:
            print("[NOTICE] Could not set @everyone Create Invite automatically:", exc)
            print("         Enable Create Invite manually in Server Settings > Roles > @everyone.")
    member_id = role_ids.get("Member")
    if MODE == "apply" and not member_id:
        raise RuntimeError("Cannot gate channels: Member role was not created")
    member_id = member_id or "000000000000000000"
    staff_ids = [role_ids[name] for name in STAFF if name in role_ids]
    # Fail before restricting channels if the bot cannot assign the Member role.
    if MODE == "apply":
        fresh_roles = request("GET", "/guilds/" + GUILD + "/roles")
        positions = {str(r["id"]): int(r["position"]) for r in fresh_roles}
        bot_member = request("GET", "/guilds/" + GUILD + "/members/" + str(bot["id"]))
        bot_rank = max([positions.get(str(r), -1) for r in bot_member.get("roles", [])] or [-1])
        member_rank = positions.get(str(member_id), -1)
        print(f"[CHECK] Bot role position: {bot_rank}; Member role position: {member_rank}", flush=True)
        if bot_rank <= member_rank:
            raise RuntimeError(
                "DISCORD ROLE ORDER: Egypt YDNA Bot is not above the Member role. "
                "In Discord Server Settings > Roles, move the 'Egypt YDNA Bot' role "
                "higher than 'Member'. Save the change, then re-run apply. "
                f"Bot position={bot_rank}; Member position={member_rank}.")
    channels = request("GET", "/guilds/" + GUILD + "/channels")
    print("\n== CATEGORIES AND CHANNELS ==")
    for category, items in DESIGN:
        cat, is_old = find_channel(channels, category, 4, CATEGORY_ALIASES.get(category, []))
        if cat and is_old:
            change("PATCH", "/channels/" + str(cat["id"]), {"name": category},
                   f"rename existing category {cat['name']} -> {category}")
            cat["name"] = category
        if not cat:
            cat = change("POST", f"/guilds/{GUILD}/channels",
                         {"type": 4, "name": category}, "create category " + category)
            if cat: channels.append(cat)
        if not cat:
            print("[PREVIEW] members and channel permissions will be applied in actual run")
        for i, (name, kind, access, topic) in enumerate(items):
            if kind == 15 and not community:
                print("[SKIP] forum", name, "requires Community mode")
                continue
            old, renamed = find_channel(channels, name, kind, CHANNEL_ALIASES.get(name, []))
            if not old:
                # Important: no destructive conversion from text channels to forums.
                data = {"type": kind, "name": name, "topic": topic, "position": i}
                if cat: data["parent_id"] = cat["id"]
                if MODE == "apply":
                    data["permission_overwrites"] = overlays(
                        None, access, member_id, staff_ids, bot["id"], kind)
                old = change("POST", f"/guilds/{GUILD}/channels",
                             data, f"create {name} in {category}")
                if old:
                    channels.append(old)
                    if name in MESSAGES:
                        try:
                            request("POST", "/channels/" + str(old["id"]) + "/messages",
                                    {"content": MESSAGES[name], "allowed_mentions": {"parse": []}})
                            print("[POSTED] starter:", name)
                        except RuntimeError as error:
                            print("[NOTICE] Cannot post starter:", error)
            else:
                data = {}
                if renamed: data["name"] = name
                if cat and str(old.get("parent_id")) != str(cat["id"]):
                    data["parent_id"] = str(cat["id"])
                if MODE == "apply":
                    new_permissions = overlays(old, access, member_id, staff_ids, bot["id"], kind)
                    if new_permissions != old.get("permission_overwrites", []):
                        data["permission_overwrites"] = new_permissions
                if data:
                    change("PATCH", "/channels/" + str(old["id"]), data,
                           f"align existing channel {old['name']} in {category} (preserve messages)")
                else:
                    print("[EXISTS] unchanged:", name)
    # Post a single verification prompt in the new, read-only verification channel.
    # The recurring verifier uses this exact marker; the prompt is never deleted.
    if MODE == "apply":
        verify = next((ch for ch in channels if ch["name"] == "verification" and ch["type"] == 0), None)
        if not verify:
            raise RuntimeError("Cannot enable verification gate: #verification is missing")
        recent = request("GET", "/channels/" + str(verify["id"]) + "/messages?limit=100")
        found = next((m for m in recent if m.get("author", {}).get("id") == str(bot["id"])
                      and "**EGYPT Y-DNA VERIFICATION**" in m.get("content", "")), None)
        if not found:
            found = request("POST", "/channels/" + str(verify["id"]) + "/messages",
                {"content": MESSAGES["verification"], "allowed_mentions": {"parse": []}})
            print("[POSTED] verification prompt")
        try:
            import urllib.parse
            emoji = urllib.parse.quote("✅", safe="")
            request("PUT", "/channels/" + str(verify["id"]) +
                    "/messages/" + str(found["id"]) + "/reactions/" + emoji + "/@me")
            print("[READY] Members can react with ✅ in #verification")
        except RuntimeError as error:
            # Gate should not be enabled if reacting is impossible.
            raise RuntimeError("Verification reaction could not be created: " + str(error))
    elif MODE == "preview":
        print("[PREVIEW] ensure one ✅ verification prompt exists")

    # Ensure English appears first, ahead of Arabic, within the community section.
    english = next((c for c in channels if c["type"] == 0 and c["name"] == "english-chat"), None)
    arabic = next((c for c in channels if c["type"] == 0 and c["name"] == "arabic-chat"), None)
    if english and arabic:
        change("PATCH", f"/guilds/{GUILD}/channels",
               [{"id": str(english["id"]), "position": 0},
                {"id": str(arabic["id"]), "position": 1}],
               "place #english-chat before #arabic-chat")
    elif MODE == "preview":
        print("[PREVIEW] #english-chat will be positioned before #arabic-chat")

    # Post new rule version once, even in existing channels. Avoid reposting on re-run.
    if MODE == "apply":
        for channel_name in ("rules", "server-guide"):
            target = next((ch for ch in channels if ch["type"] == 0 and ch["name"] == channel_name), None)
            if not target: continue
            try:
                recent = request("GET", "/channels/" + str(target["id"]) + "/messages?limit=50")
                marker = "To unlock the server, read these rules" if channel_name == "rules" else "The Member role is assigned automatically"
                if not any(marker in m.get("content", "") for m in recent):
                    request("POST", "/channels/" + str(target["id"]) + "/messages",
                            {"content": MESSAGES[channel_name], "allowed_mentions": {"parse": []}})
                    print("[POSTED] updated information:", channel_name)
            except RuntimeError as error:
                print("[NOTICE] Could not check/post updated content:", error)

    # Legacy template channels must not bypass the member approval gate.
    for ch in channels:
        if (ch["name"] == "general" and ch["type"] in (0, 2)) or (
            ch["name"] == "snp-analysis" and ch["type"] == 0
        ):
            if MODE == "apply":
                perm = overlays(ch, "members", member_id, staff_ids, bot["id"], ch["type"])
                change("PATCH", "/channels/" + str(ch["id"]),
                       {"permission_overwrites": perm},
                       "restrict legacy " + ch["name"] + " to approved members")
            else:
                print("[PREVIEW] gate legacy", ch["name"], "for approved members")
    print("\nNotes:")
    print("- Existing messages and old channels are preserved; no channel/role deletions.")
    print("- Origin and Y-DNA roles are SELF-DECLARED and never confer staff powers.")
    print("- Members unlock hidden channels by reacting ✅ in #verification.")
    print("- GitHub scheduled verifier assigns Member automatically (usually 5+ minutes).")
    print("- Assign moderator role management rights and position manually if needed.")
    print("- Private #mod-log is NOT an automatic join/leave logger; native Discord")
    print("  System Messages can announce joins in #welcome.")
    print("- Optional native Rules Screening requires separate setup in Discord and")
    print("  can add a second confirmation step before emoji reaction is allowed.")
    print("- Configure role-selection via Discord Community Onboarding on desktop.")
    print("- Existing channels with old/extra names remain; review them manually.")
    if not community:
        print("- Enable Community and re-run apply for forum channels.")
    if MODE == "preview":
        print("PREVIEW ONLY — nothing changed; re-run mode=apply to execute.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as exc:
        print("FAILED:", exc, file=sys.stderr)
        sys.exit(1)
