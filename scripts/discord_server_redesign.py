#!/usr/bin/env python3
"""Egypt Y-DNA Discord redesign. Preview-only by default, no deletions.

Existing categories/channels are renamed or moved only where explicitly
mapped below. Member verification is manual: only staff assign 'Member'.
Discord's Apply-to-Join and Onboarding must be enabled separately in Discord.
"""
import json, os, sys, time, urllib.error, urllib.request

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
MODE = os.getenv("MODE", "preview").strip()
BASE = "https://discord.com/api/v10"
INVITE = 1 << 0
VIEW = 1 << 10
SEND = 1 << 11
THREAD_SEND = 1 << 38
CONNECT = 1 << 20

STAFF = ["Administrator", "Moderator"]
CORE = ["Founder", "Administrator", "Moderator", "Member",
        "Research Contributor", "Verified Y-DNA Tester"]
# This is one combined, self-reported geographical-origin group.
# Regions refer to geography, NOT genetic/ethnic classifications.
ORIGIN = [
    "North Africa", "West Africa", "Central Africa", "East Africa", "Southern Africa",
    "Egypt", "Maghreb", "Nile Valley / Nubia", "Horn of Africa",
    "Northern Europe", "Western Europe", "Southern Europe", "Eastern Europe",
    "Levant", "Arabian Peninsula", "Mesopotamia", "Anatolia", "Caucasus",
    "Iranian Plateau", "Central Asia", "South Asia", "East Asia", "Southeast Asia",
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
ROLES = [(n, "staff") for n in CORE[:3]] + [
    (n, "member") for n in CORE[3:]
] + [(n, "origin") for n in ORIGIN] + [(n, "haplo") for n in HAPLOS]

# (target name, kind, permission mode, information/description)
DESIGN = [
    ("📌 START HERE", [
        ("welcome", 0, "read", "Welcome to the Egypt Y-DNA community."),
        ("rules", 0, "read", "Community rules and safety information."),
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
    "By participating you agree to these rules."
)
MESSAGES = {
    "welcome": "🧬 **Welcome to Egypt Y-DNA!**\nInternational Egyptian Y-DNA research and genetic genealogy community.\nMain chat: #english-chat | Arabic: #arabic-chat\nProject: https://egyptydna.github.io/Egypt-Y-DNA/\nPlease read #rules. New members are approved by staff.",
    "rules": RULES,
    "server-guide": "📖 **Getting started**\nJoin the main discussions in #english-chat. Share one sourced result per post in #submit-results; note your terminal confirmed SNP, testing platform, source, and Egyptian governorate if publicly documented or consented. Do not upload private DNA files.\nChoose any applicable geographical-origin and Y-DNA roles (self-declared); these never prove ancestry. Moderators may assign the Member role after review.",
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
    # Preserve any unrelated custom overwrites.
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
            set_permission(id, 0, VIEW | SEND | THREAD_SEND, 0)
    elif access == "read":
        set_permission(GUILD, 0, VIEW | INVITE, SEND | THREAD_SEND)
        set_permission(member_id, 0, VIEW | INVITE, SEND | THREAD_SEND)
        for id in staff_ids:
            set_permission(id, 0, VIEW | SEND | THREAD_SEND, 0)
    elif access == "members":
        set_permission(GUILD, 0, VIEW | INVITE, SEND | THREAD_SEND)
        set_permission(member_id, 0, VIEW | INVITE | SEND | THREAD_SEND, 0)
        for id in staff_ids:
            set_permission(id, 0, VIEW | INVITE | SEND | THREAD_SEND, 0)
    elif access == "voice":
        set_permission(GUILD, 0, VIEW | INVITE, CONNECT)
        set_permission(member_id, 0, VIEW | INVITE | CONNECT, 0)
        for id in staff_ids:
            set_permission(id, 0, VIEW | INVITE | CONNECT, 0)
    set_permission(bot_id, 1, VIEW | SEND | THREAD_SEND, 0)
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
    if MODE not in ("preview", "apply"):
        raise ValueError("MODE must be preview or apply")
    if not TOKEN or not GUILD.isdecimal():
        raise ValueError("GitHub secrets DISCORD_BOT_TOKEN and DISCORD_GUILD_ID required")
    guild = request("GET", "/guilds/" + GUILD)
    bot = request("GET", "/users/@me")
    print("Server:", guild["name"], "| mode:", MODE, "| bot:", bot["username"])
    community = "COMMUNITY" in guild.get("features", [])
    existing_roles = request("GET", "/guilds/" + GUILD + "/roles")
    existing_by_name = {r["name"].casefold(): r for r in existing_roles}
    role_ids = {}
    print("\n== SELF-SELECTABLE ROLES / NO SPECIAL PERMISSIONS ==")
    for name, group in ROLES:
        old = existing_by_name.get(name.casefold())
        if old:
            role_ids[name] = str(old["id"])
            if group in ("origin", "haplo") and int(old["permissions"]) != 0:
                change("PATCH", "/guilds/" + GUILD + "/roles/" + str(old["id"]),
                       {"permissions": "0"}, "align neutral role permissions: " + name)
            else:
                print("[EXISTS]", group, "role:", name)
        else:
            created = change("POST", "/guilds/" + GUILD + "/roles",
                  {"name": name, "permissions": "0", "mentionable": False},
                  f"create neutral {group} role: {name}")
            if created:
                role_ids[name] = str(created["id"])
    everyone = next((r for r in existing_roles if str(r["id"]) == GUILD), None)
    if everyone and not (int(everyone["permissions"]) & INVITE):
        change("PATCH", f"/guilds/{GUILD}/roles/{GUILD}",
               {"permissions": str(int(everyone["permissions"]) | INVITE)},
               "permit all members to create server invitations")
    member_id = role_ids.get("Member")
    if MODE == "apply" and not member_id:
        raise RuntimeError("Cannot gate channels: Member role was not created")
    member_id = member_id or "000000000000000000"
    staff_ids = [role_ids[name] for name in STAFF if name in role_ids]
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
                marker = "**EGYPT Y-DNA — COMMUNITY RULES**" if channel_name == "rules" else "**Getting started**"
                if not any(marker in m.get("content", "") for m in recent):
                    request("POST", "/channels/" + str(target["id"]) + "/messages",
                            {"content": MESSAGES[channel_name], "allowed_mentions": {"parse": []}})
                    print("[POSTED] updated information:", channel_name)
            except RuntimeError as error:
                print("[NOTICE] Could not check/post updated content:", error)

    # Apply the same Member role approval gate to legacy public template chat.
    for ch in channels:
        if ch["type"] == 0 and ch["name"] == "general":
            if MODE == "apply":
                perm = overlays(ch, "members", member_id, staff_ids, bot["id"], ch["type"])
                change("PATCH", "/channels/" + str(ch["id"]),
                       {"permission_overwrites": perm},
                       "restrict legacy #general sending to approved members")
            else:
                print("[PREVIEW] gate legacy #general for approved members")
    print("\nNotes:")
    print("- Existing messages and old channels are preserved; no channel/role deletions.")
    print("- Origin and Y-DNA roles are SELF-DECLARED and never confer staff powers.")
    print("- New users must be assigned 'Member' by staff before sending in managed chats.")
    print("- Assign moderator role management rights and position manually if needed.")
    print("- Private #mod-log is NOT an automatic join/leave logger; native Discord")
    print("  System Messages can announce joins in #welcome.")
    print("- Enable Rule Screening and (if offered) Apply to Join under Discord settings.")
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
