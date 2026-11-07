#!/usr/bin/env python3
"""Scheduled, free Discord verification gate using official REST API.

Members accept server rules by reacting ✅ to the bot's pinned-like
verification prompt. No always-on bot, server, or third-party bot required.
Runs periodically via GitHub Actions. Never removes roles or bans people.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
BASE = "https://discord.com/api/v10"
MARKER = "**EGYPT Y-DNA VERIFICATION**"
EMOJI = urllib.parse.quote("✅", safe="")


def api(method, path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    headers = {
        "Authorization": "Bot " + TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "EgyptYDNAVerification/1.0",
    }
    for attempt in range(6):
        request = urllib.request.Request(
            BASE + path, data=payload, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as result:
                response = result.read()
                time.sleep(0.15)
                return json.loads(response) if response else None
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors="replace")
            if error.code == 429 and attempt < 5:
                try:
                    wait = min(30, float(json.loads(body).get("retry_after", 2)))
                except (ValueError, TypeError):
                    wait = 2
                time.sleep(wait + 0.5)
                continue
            if error.code == 404:
                return None
            raise RuntimeError(
                f"{method} {path}: HTTP {error.code}: {body[:350]}"
            ) from error
    raise RuntimeError("Could not complete Discord request (rate limit).")


def main():
    if not TOKEN or not GUILD.isdecimal():
        raise RuntimeError(
            "Missing GitHub Actions secrets DISCORD_BOT_TOKEN or DISCORD_GUILD_ID"
        )
    bot = api("GET", "/users/@me")
    roles = api("GET", f"/guilds/{GUILD}/roles")
    if not bot or not roles:
        raise RuntimeError("Discord bot cannot read server roles")
    member = next((role for role in roles if role["name"] == "Member"), None)
    if not member:
        print("SKIP: No Member role yet. Run Discord Server Setup with apply first.")
        return

    channels = api("GET", f"/guilds/{GUILD}/channels")
    verify = next(
        (ch for ch in channels or []
         if ch.get("type") == 0 and ch.get("name") == "verification"),
        None,
    )
    if not verify:
        print("SKIP: #verification is not set up yet.")
        return

    messages = api(
        "GET", f"/channels/{verify['id']}/messages?limit=100"
    )
    prompt = next(
        (msg for msg in messages or []
         if msg.get("author", {}).get("id") == bot["id"]
         and MARKER in msg.get("content", "")),
        None,
    )
    if not prompt:
        print("SKIP: No bot-owned verification prompt is visible.")
        return

    modlog = next(
        (ch for ch in channels or []
         if ch.get("type") == 0 and ch.get("name") == "mod-log"),
        None,
    )

    channel_id, message_id = verify["id"], prompt["id"]
    after = None
    seen = 0
    assigned = 0
    errors = 0
    while True:
        url = (
            f"/channels/{channel_id}/messages/{message_id}"
            f"/reactions/{EMOJI}?limit=100"
        )
        if after:
            url += "&after=" + urllib.parse.quote(str(after), safe="")
        reactions = api("GET", url)
        if reactions is None:
            raise RuntimeError("Verification message or emoji reaction is missing")
        if not reactions:
            break
        for user in reactions:
            if user.get("bot"):
                continue
            user_id = str(user["id"])
            seen += 1
            try:
                info = api("GET", f"/guilds/{GUILD}/members/{user_id}")
                if not info:
                    # Former member: do not restore access.
                    continue
                if info.get("pending"):
                    # Respect Discord native Rules Screening if enabled.
                    continue
                if str(member["id"]) in info.get("roles", []):
                    continue
                api(
                    "PUT",
                    f"/guilds/{GUILD}/members/{user_id}/roles/{member['id']}",
                )
                assigned += 1
                print("Verified member:", user_id)
                if modlog:
                    try:
                        api("POST", f"/channels/{modlog['id']}/messages", {
                            "content": (
                                f"✅ Verification: <@{user_id}> accepted #rules "
                                "via ✅ reaction and received the Member role."
                            ),
                            "allowed_mentions": {"parse": []},
                        })
                    except RuntimeError as error:
                        print("Notice: could not write staff log:", error)
            except RuntimeError as error:
                errors += 1
                print(f"ERROR assigning member {user_id}: {error}", file=sys.stderr)
        if len(reactions) < 100:
            break
        after = str(reactions[-1]["id"])

    print(
        f"Completed. Human reactions: {seen}; "
        f"newly verified: {assigned}; errors: {errors}"
    )
    if errors:
        raise RuntimeError(
            "Some members could not be assigned; verify bot's Manage Roles "
            "permission and place its role above Member."
        )


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, urllib.error.URLError) as exc:
        print("VERIFICATION ERROR:", exc, file=sys.stderr)
        sys.exit(1)
