#!/usr/bin/env python3
"""Egypt Y-DNA: automatically grant neutral Verified to human members on join.

No ✅ reaction, moderator approval or manual application. GitHub Actions
checks periodically; this is not a live 24/7 Discord Gateway listener and
runs can be delayed.

Primary method: List Guild Members (requires privileged GUILD_MEMBERS intent).
Fallback: parse Discord-native USER_JOIN messages (type 7) in the system
join channel and use Get Guild Member for individual joined users; this does
not require a privileged member-list intent. The fallback may miss users if
join announcements were off or their messages have been deleted. It cannot
guarantee instant or exhaustive verification without the Members Intent.

Never assigns staff or privileged roles, never kicks, bans, prunes, revokes
roles, or changes guild/channel permission overwrites.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from discord_join_feed import JOIN_NAME

GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
BASE = "https://discord.com/api/v10"
MANAGE_ROLES = 1 << 28
ADMINISTRATOR = 1 << 3
JOIN_MESSAGE_TYPE = 7
MAX_JOIN_MESSAGES = 2000
MAX_MEMBERS = 100000


def api(method, path, data=None, allow_404=False, allow_403=False):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        request = urllib.request.Request(
            BASE + path, data=body, method=method,
            headers={
                "Authorization": "Bot " + TOKEN,
                "Content-Type": "application/json",
                "User-Agent": "EgyptYDNAAutoVerification/5.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read()
                time.sleep(0.12)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            body_error = error.read().decode(errors="replace")
            if allow_404 and error.code == 404:
                return None
            if allow_403 and error.code == 403:
                return None
            if error.code == 429 and attempt < 5:
                try:
                    pause = min(30, float(json.loads(body_error).get("retry_after", 2)))
                except (TypeError, ValueError):
                    pause = 2
                time.sleep(pause + 0.5)
                continue
            raise RuntimeError(
                f"Discord HTTP {error.code}: {method} {path}: {body_error[:250]}"
            ) from error
    raise RuntimeError("Discord rate-limit retry budget exhausted")


def member_list():
    """Return full member list, or None when privileged intent is unavailable."""
    items = []
    after = None
    while len(items) < MAX_MEMBERS:
        path = f"/guilds/{GUILD}/members?limit=1000"
        if after:
            path += "&after=" + urllib.parse.quote(after, safe="")
        batch = api("GET", path, allow_403=True)
        if batch is None:
            print("[NOTICE] Full member list unavailable (Server Members Intent "
                  "disabled or missing). Checking native join notices instead.",
                  flush=True)
            return None
        if not isinstance(batch, list):
            raise RuntimeError("Discord returned invalid member list data.")
        items.extend(batch)
        if len(batch) < 1000:
            return items
        after = str(batch[-1]["user"]["id"])
    raise RuntimeError("Member-list safety limit exceeded; do not silently truncate.")


def members_from_join_messages(guild):
    """Enumerate join announcements from the exact configured Discord system channel."""
    channel_id = str(guild.get("system_channel_id") or "")
    if not channel_id or not channel_id.isdecimal():
        raise RuntimeError(
            "[ACTION REQUIRED] No Discord system join channel configured. "
            "Run Egypt Y-DNA Join Feed > apply, or enable Server Members Intent "
            "in Discord Developer Portal > Bot."
        )
    if int(guild.get("system_channel_flags") or 0) & 1:
        raise RuntimeError(
            "[ACTION REQUIRED] Discord system join announcements are disabled. "
            "Run Egypt Y-DNA Join Feed > apply to enable them, or enable "
            "Server Members Intent."
        )
    channels = api("GET", f"/guilds/{GUILD}/channels")
    channel = next(
        (c for c in channels if str(c.get("id")) == channel_id
         and c.get("type") == 0), None
    )
    if channel is None:
        raise RuntimeError(
            "Configured Discord system join channel not found or is not text."
        )
    print("[CHECK] Using native join feed:", channel["name"],
          "(no Members Intent required)", flush=True)
    users = []
    seen_ids = set()
    before = None
    scanned = 0
    for _ in range(MAX_JOIN_MESSAGES // 100):
        path = f"/channels/{channel_id}/messages?limit=100"
        if before:
            path += "&before=" + before
        messages = api("GET", path) or []
        if not messages:
            break
        scanned += len(messages)
        for message in messages:
            if message.get("type") != JOIN_MESSAGE_TYPE:
                continue
            author = message.get("author") or {}
            uid = str(author.get("id") or "")
            if not uid.isdecimal() or uid in seen_ids or author.get("bot"):
                continue
            seen_ids.add(uid)
            users.append(uid)
        if len(messages) < 100:
            break
        before = str(messages[-1]["id"])
    print("[CHECK] Join messages scanned:", scanned,
          "| unique human join notices:", len(users), flush=True)
    if not users:
        raise RuntimeError(
            "[ACTION REQUIRED] No native join notices found in the system "
            "channel. Automatic verification cannot be confirmed. "
            "Enable Server Members Intent in Discord Developer Portal > Bot "
            "or fix Discord's native join notifications."
        )
    return users


def assign_verified(member, uid, verified_id):
    """Return classification; only grant the nonprivileged Verified role."""
    if not member:
        return "left"
    user = member.get("user") or {}
    if user.get("bot") or str(user.get("id") or "") != str(uid):
        return "bot_or_invalid"
    assigned = {str(role) for role in member.get("roles", [])}
    if verified_id in assigned:
        return "already"
    api("PUT", f"/guilds/{GUILD}/members/{uid}/roles/{verified_id}")
    return "granted"


def main():
    if not GUILD.isdecimal() or not TOKEN:
        raise ValueError("Missing DISCORD_GUILD_ID / DISCORD_BOT_TOKEN secrets")
    guild = api("GET", f"/guilds/{GUILD}")
    roles = api("GET", f"/guilds/{GUILD}/roles")
    verified_options = [r for r in roles if r.get("name", "").casefold() == "verified"]
    if len(verified_options) != 1:
        raise RuntimeError(
            "[ACTION REQUIRED] Exactly one Verified role must exist."
        )
    verified = verified_options[0]
    if int(verified.get("permissions", 0)):
        raise RuntimeError(
            "[SAFETY] Verified role has nonzero server-wide permissions; "
            "automatic assignment refused. Remove extra permissions first."
        )
    bot = api("GET", "/users/@me")
    bot_member = api("GET", f"/guilds/{GUILD}/members/{bot['id']}")
    by_id = {str(r["id"]): r for r in roles}
    top = max(
        (int(by_id[str(r)]["position"]) for r in bot_member.get("roles", [])
         if str(r) in by_id), default=-1
    )
    if top <= int(verified["position"]):
        raise RuntimeError(
            "[ACTION REQUIRED] Discord role hierarchy: move Egypt YDNA Bot "
            "ABOVE Verified under Server Settings > Roles. "
            f"Bot top={top}, Verified={verified['position']}."
        )
    permissions = int(by_id.get(GUILD, {}).get("permissions", 0))
    for rid in bot_member.get("roles", []):
        if str(rid) in by_id:
            permissions |= int(by_id[str(rid)].get("permissions", 0))
    if not permissions & (MANAGE_ROLES | ADMINISTRATOR):
        raise RuntimeError("[ACTION REQUIRED] Bot needs Manage Roles.")
    print("[CHECK] Server:", guild.get("name"),
          "| neutral Verified role id:", verified["id"],
          "| hierarchy and bot permissions OK", flush=True)

    listed = member_list()
    result = {
        "checked": 0, "already": 0, "granted": 0, "bot_or_invalid": 0,
        "left": 0, "errors": 0, "native_screening_pending": 0,
    }
    verified_id = str(verified["id"])
    if listed is not None:
        source = "full_member_list"
        candidates = [
            (str(member.get("user", {}).get("id") or ""), member)
            for member in listed
        ]
    else:
        source = "native_join_messages"
        ids = members_from_join_messages(guild)
        candidates = [(uid, None) for uid in ids]
    for uid, listed_member in candidates:
        if not uid.isdecimal():
            result["bot_or_invalid"] += 1
            continue
        try:
            member = (
                listed_member if listed_member is not None
                else api("GET", f"/guilds/{GUILD}/members/{uid}", allow_404=True)
            )
            result["checked"] += 1
            if member and member.get("pending", False) is True:
                result["native_screening_pending"] += 1
            outcome = assign_verified(member, uid, verified_id)
            result[outcome] += 1
        except RuntimeError as error:
            result["errors"] += 1
            print("[ERROR] Discord declined a Verified assignment:",
                  str(error).split("Discord HTTP")[0].strip() or "Discord API error",
                  file=sys.stderr, flush=True)
    print("[SUMMARY] source=", source,
          "| checked=", result["checked"],
          "| newly_verified=", result["granted"],
          "| already_verified=", result["already"],
          "| bots_or_invalid=", result["bot_or_invalid"],
          "| left_server=", result["left"],
          "| native_screening_pending=", result["native_screening_pending"],
          "| errors=", result["errors"], flush=True)
    if result["native_screening_pending"]:
        print("[NOTICE] Some members still have Discord native Membership "
              "Screening pending. Verified can be assigned, but Discord may "
              "withhold access until its native screening is completed.",
              flush=True)
    if source == "native_join_messages":
        print("[LIMITATION] Join-feed fallback only covers available native "
              "join notices. Enable Server Members Intent for exhaustive "
              "coverage. Scheduled GitHub runs may be significantly delayed.",
              flush=True)
    if result["errors"]:
        raise RuntimeError(
            f"{result['errors']} Verified assignments failed; inspect Discord bot permissions."
        )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
