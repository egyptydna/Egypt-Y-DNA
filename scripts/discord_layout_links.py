#!/usr/bin/env python3
"""Idempotent final layout/privacy/link adjustments for Egypt Y-DNA Discord.

Run with MODE=preview first, then MODE=apply. Never deletes messages or channels.
Existing staff-only category is made private even for old channels. Discord
server owner always has access. Moderator and Administrator roles get access.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://discord.com/api/v10"
GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
MODE = os.getenv("MODE", "preview").strip().lower()
VIEW = 1 << 10
SEND = 1 << 11
READ_HISTORY = 1 << 16
THREAD_SEND = 1 << 38

SITE_TEXT = "🌐 **Official Website**\nhttps://egyptydna.github.io/Egypt-Y-DNA/"
TWITTER_TEXT = "𝕏 **Official X / Twitter**\nhttps://x.com/egyptydna"
CATEGORY_NAMES = [
    ("📌 START HERE", "📌 INFORMATION"),
    ("🌍 COMMUNITY", "💬 COMMUNITY"),
    ("🧬 Y-DNA RESEARCH", "🧬 Y-DNA RESULTS"),
    ("🗺️ RESOURCES", "🗺️ EGYPTIAN ORIGINS"),
    ("🔒 STAFF", "🔒 STAFF ONLY"),
]


def api(method, endpoint, data=None):
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        request = urllib.request.Request(
            BASE + endpoint, method=method, data=payload,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNALayout/1.0"}
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                result = response.read()
                time.sleep(0.25)
                return json.loads(result) if result else None
        except urllib.error.HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            if error.code == 429 and attempt < 5:
                try:
                    pause = min(float(json.loads(message).get("retry_after", 2)), 30)
                except (ValueError, TypeError):
                    pause = 2
                time.sleep(pause + 0.5)
                continue
            raise RuntimeError(
                f"{method} {endpoint}: Discord HTTP {error.code}: {message[:400]}"
            )
    raise RuntimeError("Discord API rate-limit retry budget exhausted")


def change(method, endpoint, data, label):
    if MODE == "preview":
        print("[PREVIEW]", label, flush=True)
        return None
    result = api(method, endpoint, data)
    print("[APPLIED]", label, flush=True)
    return result


def role_overwrites(staff_ids, bot_id):
    """Exact whitelist; old custom overrides cannot accidentally leak staff data."""
    result = [
        {"id": GUILD, "type": 0, "allow": "0", "deny": str(VIEW | SEND | THREAD_SEND)}
    ]
    for role_id in staff_ids:
        result.append({
            "id": str(role_id), "type": 0,
            "allow": str(VIEW | SEND | READ_HISTORY | THREAD_SEND),
            "deny": "0",
        })
    result.append({
        "id": str(bot_id), "type": 1,
        "allow": str(VIEW | SEND | READ_HISTORY | THREAD_SEND), "deny": "0",
    })
    return result


def main():
    if MODE not in ("preview", "apply"):
        raise ValueError("MODE must be preview or apply")
    if not GUILD.isdecimal() or not TOKEN:
        raise ValueError("Set DISCORD_GUILD_ID and DISCORD_BOT_TOKEN as GitHub Secrets")
    guild = api("GET", "/guilds/" + GUILD)
    bot = api("GET", "/users/@me")
    roles = api("GET", "/guilds/" + GUILD + "/roles")
    channels = api("GET", "/guilds/" + GUILD + "/channels")
    role_ids = []
    for role_name in ("Founder", "Moderator", "Administrator"):
        found = next((r for r in roles if r["name"].casefold() == role_name.casefold()), None)
        if not found:
            raise RuntimeError("Missing role " + role_name + "; run initial setup first")
        role_ids.append(str(found["id"]))

    print("Server:", guild["name"], "| Mode:", MODE, flush=True)
    print("1) COMMUNITY immediately above Y-DNA RESEARCH")
    ordered = []
    for canonical, alias in CATEGORY_NAMES:
        found = next(
            (c for c in channels if c["type"] == 4 and c["name"] in (canonical, alias)),
            None,
        )
        if found:
            ordered.append(found)
        else:
            print("[NOTE] Category is missing:", canonical)
    if ordered:
        payload = [{"id": str(c["id"]), "position": position}
                   for position, c in enumerate(ordered)]
        # API position values are category positions within guild channels.
        change("PATCH", "/guilds/" + GUILD + "/channels", payload,
               "reorder START HERE > COMMUNITY > Y-DNA RESEARCH > RESOURCES > STAFF")

    print("2) STAFF category restricted to moderators and administrators")
    staff = next(
        (c for c in channels if c["type"] == 4
         and c["name"] in ("🔒 STAFF", "🔒 STAFF ONLY")),
        None,
    )
    if not staff:
        staff = change("POST", "/guilds/" + GUILD + "/channels",
                       {"type": 4, "name": "🔒 STAFF",
                        "permission_overwrites": role_overwrites(role_ids, bot["id"])},
                       "create private STAFF category")
        if staff:
            channels.append(staff)

    allowed = role_overwrites(role_ids, bot["id"])
    if staff:
        if staff.get("permission_overwrites", []) != allowed:
            change("PATCH", "/channels/" + str(staff["id"]),
                   {"permission_overwrites": allowed},
                   "make STAFF category inaccessible to all non-staff roles")
        staff_channels = [c for c in channels
                          if str(c.get("parent_id")) == str(staff["id"])]
        for channel in staff_channels:
            if channel.get("permission_overwrites", []) != allowed:
                change("PATCH", "/channels/" + str(channel["id"]),
                       {"permission_overwrites": allowed},
                       "make STAFF channel private: #" + channel["name"])

    print("3) Archive unnecessary #snp-analysis without deleting its messages")
    analysis = next((c for c in channels if c["type"] == 0 and
                     c["name"] in ("snp-analysis", "archived-snp-analysis")), None)
    if analysis:
        payload = {
            "name": "archived-snp-analysis",
            "permission_overwrites": allowed,
        }
        if staff:
            payload["parent_id"] = str(staff["id"])
        if (analysis["name"] != payload["name"] or
            analysis.get("permission_overwrites", []) != allowed or
            (staff and str(analysis.get("parent_id")) != str(staff["id"]))):
            change("PATCH", "/channels/" + str(analysis["id"]), payload,
                   "hide and archive former #snp-analysis in STAFF")
        else:
            print("[EXISTS] SNP analysis already archived")
    else:
        print("[EXISTS] No #snp-analysis needs archiving")

    print("4) #useful-links: TWO messages, official website first, X/Twitter second")
    useful = next((c for c in channels
                   if c["type"] == 0 and c["name"] == "useful-links"), None)
    if not useful:
        print("[NOTE] #useful-links missing; run initial Discord setup first")
    elif MODE == "preview":
        print("[PREVIEW] replace old bot Research resources post with website link")
        print("[PREVIEW] add X/Twitter as a separate message; no extra research links")
    else:
        path = "/channels/" + str(useful["id"])
        messages = api("GET", path + "/messages?limit=100")
        owned = [m for m in messages
                 if str(m.get("author", {}).get("id")) == str(bot["id"])]
        site = next((m for m in owned if m.get("content") == SITE_TEXT), None)
        twitter = next((m for m in owned if m.get("content") == TWITTER_TEXT), None)
        legacy = next((m for m in owned
                       if "**Research resources**" in m.get("content", "") or
                       "YFull: https://www.yfull.com/tree/" in m.get("content", "")),
                      None)
        # If the original links post exists, edit it in place. No old links are lost
        # from unrelated messages and no channel message histories are deleted.
        if legacy:
            api("PATCH", path + "/messages/" + str(legacy["id"]),
                {"content": SITE_TEXT, "allowed_mentions": {"parse": []}})
            print("[APPLIED] old research-resources bot message now has only website")
            site = legacy
        if not site:
            site = api("POST", path + "/messages",
                       {"content": SITE_TEXT, "allowed_mentions": {"parse": []}})
            print("[APPLIED] created separate website message")
        if not twitter:
            api("POST", path + "/messages",
                {"content": TWITTER_TEXT, "allowed_mentions": {"parse": []}})
            print("[APPLIED] created separate X/Twitter message")
        else:
            print("[EXISTS] separate X/Twitter message")

    print("DONE. No channels or user messages were deleted.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
