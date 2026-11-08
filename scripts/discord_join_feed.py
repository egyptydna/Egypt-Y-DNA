#!/usr/bin/env python3
"""Convert the EXISTING Egypt Y-DNA #general into a read-only join feed.

Discord's native system join notifications are instant and free; no
third-party welcome bot, extra server, cron or persisted data is needed.
The source channel ID and message history are kept. This script NEVER
creates a second #general or #in channel and NEVER deletes any messages.

Preview is read-only. Apply renames #general to 🚪・in, positions it in
the existing Information/START HERE category if available, makes it
read-only for human members and designates it as the system message
channel with native join notifications enabled.
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
SOURCE_CHANNEL_ID = os.getenv(
    "DISCORD_JOIN_SOURCE_CHANNEL_ID", "1568675061039370335").strip()
JOIN_NAME = "🚪・in"
VIEW = 1 << 10
SEND = 1 << 11
READ_HISTORY = 1 << 16
CREATE_PUBLIC_THREADS = 1 << 35
CREATE_PRIVATE_THREADS = 1 << 36
SEND_IN_THREADS = 1 << 38
MANAGE_GUILD = 1 << 5
ADMINISTRATOR = 1 << 3
MANAGE_CHANNELS = 1 << 4
SUPPRESS_JOIN = 1 << 0
SUPPRESS_BOOST = 1 << 1
SUPPRESS_REMINDERS = 1 << 2

def api(method, path, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + path, method=method, data=body,
            headers={
                "Authorization": "Bot " + TOKEN,
                "Content-Type": "application/json",
                "User-Agent": "EgyptYDNAJoinChannelSetup/1.0",
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
                time.sleep(0.15)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            if error.code == 429 and attempt < 5:
                try:
                    pause = min(30, float(json.loads(detail).get("retry_after", 2)))
                except (TypeError, ValueError):
                    pause = 2
                time.sleep(pause + 0.5)
                continue
            raise RuntimeError(
                f"Discord HTTP {error.code} {method} {path}: {detail[:400]}") from error
    raise RuntimeError("Discord rate-limit retry budget exhausted")

def update(method, path, data, label):
    if MODE == "preview":
        print("[PREVIEW]", label, flush=True)
        return None
    result = api(method, path, data)
    print("[APPLIED]", label, flush=True)
    return result

def overwrite(id_, allow=0, deny=0, kind=0):
    return {
        "id": str(id_), "type": kind,
        "allow": str(allow), "deny": str(deny)
    }

def read_only_permissions(guild_id, verified_id, staff_ids, bot_id):
    deny = SEND | SEND_IN_THREADS | CREATE_PUBLIC_THREADS | CREATE_PRIVATE_THREADS
    perms = [overwrite(guild_id, allow=VIEW | READ_HISTORY, deny=deny)]
    if verified_id:
        perms.append(overwrite(verified_id, allow=VIEW | READ_HISTORY, deny=deny))
    for staff_id in staff_ids:
        perms.append(overwrite(staff_id, allow=VIEW | READ_HISTORY, deny=deny))
    perms.append(overwrite(bot_id, allow=VIEW | SEND | READ_HISTORY, kind=1))
    return perms

def normalized(overwrites):
    return sorted(
        (str(entry["id"]), int(entry["type"]),
         int(entry.get("allow", 0)), int(entry.get("deny", 0)))
        for entry in overwrites
    )

def choose_channel(channels, guild):
    text_channels = [c for c in channels if c.get("type") == 0]
    matching_id = next((c for c in text_channels if str(c["id"]) == SOURCE_CHANNEL_ID), None)
    if matching_id and matching_id["name"] in ("general", JOIN_NAME, "🚪in"):
        return matching_id
    already = [c for c in text_channels if c["name"] in (JOIN_NAME, "🚪in")]
    if len(already) == 1:
        return already[0]
    if len(already) > 1:
        raise RuntimeError("Multiple join channels exist. No channel changed.")
    general = [c for c in text_channels if c["name"] == "general"]
    if len(general) == 1:
        return general[0]
    raise RuntimeError(
        "Cannot identify a unique text #general on this server. "
        "No changes made. Set DISCORD_JOIN_SOURCE_CHANNEL_ID to the correct "
        "existing text-channel ID and run again.")

def main():
    if MODE not in ("preview", "apply"):
        raise ValueError("MODE must be preview or apply")
    if not TOKEN or not GUILD.isdecimal():
        raise ValueError("Missing GitHub Secrets DISCORD_GUILD_ID / DISCORD_BOT_TOKEN")
    guild = api("GET", f"/guilds/{GUILD}")
    bot = api("GET", "/users/@me")
    roles = api("GET", f"/guilds/{GUILD}/roles")
    member = api("GET", f"/guilds/{GUILD}/members/{bot['id']}")
    channels = api("GET", f"/guilds/{GUILD}/channels")
    chosen = choose_channel(channels, guild)
    print("[KEEP] Existing text channel", chosen["name"], "id=", chosen["id"],
          "history retained; mode=", MODE, flush=True)

    by_id = {str(role["id"]): role for role in roles}
    bot_perms = 0
    for rid in [GUILD] + list(member.get("roles", [])):
        role = by_id.get(str(rid))
        if role:
            bot_perms |= int(role.get("permissions", "0"))
    if not (bot_perms & MANAGE_GUILD or bot_perms & ADMINISTRATOR):
        raise RuntimeError(
            "[ACTION REQUIRED] The Egypt YDNA Bot needs Manage Server "
            "(Manage Guild) to set Discord's native join-message channel. "
            "Enable Manage Server for the bot without granting Administrator.")
    if not (bot_perms & MANAGE_CHANNELS or bot_perms & ADMINISTRATOR):
        raise RuntimeError(
            "[ACTION REQUIRED] The Egypt YDNA Bot needs Manage Channels "
            "to rename #general and set read-only channel permissions.")

    roles_by_name = {r["name"].casefold(): r for r in roles}
    verified = roles_by_name.get("verified")
    staff_ids = [str(roles_by_name[name]["id"])
                 for name in ("founder", "administrator", "moderator")
                 if name in roles_by_name]
    if len(staff_ids) < 3:
        raise RuntimeError(
            "[ACTION REQUIRED] Staff roles incomplete; cannot safely "
            "protect the join channel until all three exist.")

    parent = next(
        (c for c in channels if c.get("type") == 4 and
         c.get("name") in ("📌 START HERE", "📌 INFORMATION", "📜 INFORMATION",
                           "Information", "INFORMATION")), None)
    room_perms = read_only_permissions(GUILD,
                       str(verified["id"]) if verified else None,
                       staff_ids, str(bot["id"]))
    room_update = {}
    if chosen["name"] != JOIN_NAME:
        room_update["name"] = JOIN_NAME
    if parent and str(chosen.get("parent_id")) != str(parent["id"]):
        room_update["parent_id"] = str(parent["id"])
    if normalized(chosen.get("permission_overwrites", [])) != normalized(room_perms):
        room_update["permission_overwrites"] = room_perms
    topic = ("🚪 Automatic member-join announcements • Read only • "
             "Welcome to Egypt Y-DNA! Read #rules, then explore the community.")
    if chosen.get("topic") != topic:
        room_update["topic"] = topic
    if room_update:
        update("PATCH", f"/channels/{chosen['id']}", room_update,
               "rename existing #general to " + JOIN_NAME +
               ", keep history, set member read-only and place in information")
    else:
        print("[EXISTS] Join channel name, category and permissions already correct")

    flags = int(guild.get("system_channel_flags") or 0)
    # Enable native join notices (clear bit 0), suppress unrelated boost
    # and server-tip messages in this dedicated join feed. Preserve other bits.
    wanted_flags = (flags & ~SUPPRESS_JOIN) | SUPPRESS_BOOST | SUPPRESS_REMINDERS
    if (str(guild.get("system_channel_id")) != str(chosen["id"])
            or flags != wanted_flags):
        update("PATCH", f"/guilds/{GUILD}",
               {"system_channel_id": str(chosen["id"]),
                "system_channel_flags": wanted_flags},
               "enable FREE instant Discord-native join notifications in " +
               JOIN_NAME + " (no MEE6 required)")
    else:
        print("[EXISTS] Discord already posts native join messages in this channel")

    print("[DONE] " + JOIN_NAME + " will show Discord's own join notifications. "
          "Ordinary members cannot send messages or create threads. "
          "Server owner and Administrator users can always bypass channel "
          "restrictions. Existing #general messages are preserved. "
          "Fancy MEE6 image-cards require an additional bot and are NOT "
          "created by Discord's native messages.")
    if MODE == "preview":
        print("[PREVIEW ONLY] No Discord changes have been made.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
