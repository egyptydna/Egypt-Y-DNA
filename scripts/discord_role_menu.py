"""Compact, safe, manually curated Discord reaction-role catalogue.

One message can carry at most 20 different reactions, so the role selector is
split into a pinned introduction and a few themed menus. Role names here are
single, non-overlapping Y-DNA branches: no ancestor+descendant triple clicks.
Every role shown must exist in Discord and have no admin/staff permissions.
"""
# Specific geographic-origin choices, including North African nationalities.
ORIGIN_SECTIONS = [
    ("NORTH AFRICA", [
        "Egypt", "Morocco", "Algeria", "Tunisia", "Libya", "Sudan",
        "Mauritania", "North Africa", "Maghreb", "Nile Valley / Nubia",
        "Copt", "Amazighi",
    ]),
    ("AFRICA & EUROPE", [
        "West Africa", "Central Africa", "East Africa", "Southern Africa",
        "Horn of Africa", "Northern Europe", "Western Europe",
        "Southern Europe", "Balkans", "Eastern Europe",
    ]),
    ("WEST & CENTRAL ASIA", [
        "West Asia", "Levant", "Arabian Peninsula", "Mesopotamia",
        "Anatolia", "Caucasus", "Iranian Plateau", "Central Asia",
        "North Asia", "South Asia",
    ]),
    ("EAST ASIA, OCEANIA & AMERICAS", [
        "East Asia", "Southeast Asia", "Australia & New Zealand",
        "Melanesia", "Micronesia", "Polynesia", "North America",
        "Central America", "Caribbean", "South America",
        "Indigenous Peoples", "Multiple Regions",
    ]),
]
YDNA_SECTIONS = [
    ("E, J & R", [
        "E-M2", "E-M81", "E-M123", "E-V13", "E-V22", "E-V32",
        "J1-P58", "J2a", "J2b",
        "R1a", "R1b-V88", "R1b-M269", "R2",
    ]),
    ("Q, T, G, I, L & H", [
        "Q1", "Q2", "T-P77", "G1", "G2", "I1", "I2",
        "L1", "L2", "H1", "H2", "Other / unresolved",
    ]),
]
GENDER_SECTIONS = [("OPTIONAL", ["Male", "Female"])]

FLAG_EMOJIS = {
    "Egypt": "🇪🇬",
    "Morocco": "🇲🇦",
    "Algeria": "🇩🇿",
    "Tunisia": "🇹🇳",
    "Libya": "🇱🇾",
    "Sudan": "🇸🇩",
    "Mauritania": "🇲🇷",
}
GENDER_EMOJIS = {"Male": "🔵", "Female": "🌸"}
FALLBACK_EMOJIS = (
    "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟",
    "🔴", "🟠", "🟡", "🟢", "🟣", "🟤", "⚫", "⚪", "🔶", "🔷",
)
VERSION = "V2"
ROLE_MARKER = "**EGYPT Y-DNA PICKER V2:"
OVERVIEW_MARKER = "**EGYPT Y-DNA — CHOOSE YOUR ROLES**"
COUNTRY_COLORS = {
    "Morocco": 0xBC3139,
    "Algeria": 0x208A58,
    "Tunisia": 0xD44948,
    "Libya": 0x3E846C,
    "Sudan": 0xA94C42,
    "Mauritania": 0x3B9856,
}

SELECTABLE_ORIGINS = tuple(dict.fromkeys(
    name for _, names in ORIGIN_SECTIONS for name in names
))
SELECTABLE_YDNA = tuple(dict.fromkeys(
    name for _, names in YDNA_SECTIONS for name in names
))

def menu_groups(role_by_name):
    result = []
    for category, sections in (("ORIGIN", ORIGIN_SECTIONS),
                                ("Y-DNA", YDNA_SECTIONS),
                                ("GENDER", GENDER_SECTIONS)):
        for label, names in sections:
            available = [n for n in names if n.casefold() in role_by_name]
            if not available:
                continue
            if len(available) > 20:
                raise ValueError("More than 20 emoji choices in " + label)
            marker = f"{ROLE_MARKER} {category} {label}**"
            result.append((marker, category, available))
    return result

def menu_emojis(category, names):
    used = set()
    result = []
    for name in names:
        preferred = (FLAG_EMOJIS.get(name) if category == "ORIGIN"
                     else GENDER_EMOJIS.get(name) if category == "GENDER"
                     else None)
        if preferred and preferred not in used:
            emoji = preferred
        else:
            emoji = next((e for e in FALLBACK_EMOJIS if e not in used), None)
        if not emoji:
            raise ValueError("Too many distinct reaction choices")
        used.add(emoji)
        result.append(emoji)
    return result

def menu_content(marker, category, names):
    label = marker.split(": ", 1)[1].removesuffix("**")
    title = label.replace(" ORIGIN ", " — ").replace(" Y-DNA ", " — ")
    if category == "ORIGIN":
        intro = "🌍 **GEOGRAPHICAL & CULTURAL ORIGINS**"
        hint = "*Select all that apply to you. These labels are voluntary, not DNA evidence.*"
    elif category == "Y-DNA":
        intro = "🧬 **YOUR Y-DNA BRANCH**"
        hint = "*Choose your most specific known branch only. A prediction is not a confirmed SNP result.*"
    else:
        intro = "👤 **OPTIONAL ROLE**"
        hint = "*Choose Male OR Female. The role does not affect server access.*"
    lines = [marker, intro, f"**{title}**", hint, ""]
    for emoji, name in zip(menu_emojis(category, names), names):
        lines.append(f"{emoji}  **{name}**")
    lines += ["", "React to your choice below. Roles are added automatically",
              "after a scheduled check (usually a few minutes).",
              "*Verified and staff roles are never self-assignable.*"]
    return "\n".join(lines)

def overview_text(groups):
    return "\n".join([
        OVERVIEW_MARKER,
        "🌍 **Origins** — choose any applicable region or country.",
        "🧬 **Y-DNA** — select the most specific branch you know, not parent branches.",
        "👤 **Male / Female** — optional.",
        "",
        "⬇️ **Choose a role by reacting to the matching emoji in a menu below.**",
        "An Egypt 🇪🇬 or Morocco 🇲🇦 reaction gives you that role automatically",
        "when the scheduled role updater runs.",
        "",
        "**Important:** You must already be **Verified**. You cannot select",
        "Founder, Administrator, Moderator, Verified, Verified Y-DNA Tester or Bot.",
        f"**Available menus:** {len(groups)} (Discord limits reactions to 20 per message).",
    ])
