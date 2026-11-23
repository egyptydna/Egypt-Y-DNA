#!/usr/bin/env python3
"""Idempotently update only bot-owned welcome/rules posts for auto Verified.

No channel edits, no role edits, no reaction requirements, no deletions.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

from discord_rules_cleanup import MARKER as RULE_MARKER, RULES_TEXT
from discord_verification_setup import WELCOME_PROMPT

GID = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
BASE = "https://discord.com/api/v10"
WELCOME_MARKER = "👋 **EGYPT Y-DNA — WELCOME**"


def api(method, path, data=None):
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        request = urllib.request.Request(
            BASE + path, method=method, data=payload,
            headers={
                "Authorization": "Bot " + TOKEN,
                "Content-Type": "application/json",
                "User-Agent": "EgyptYDNAAutoVerificationNotices/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                body = response.read()
                time.sleep(0.1)
                return json.loads(body) if body else None
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
                f"Discord HTTP {error.code} while updating bot announcement: "
                f"{detail[:250]}"
            ) from error
    raise RuntimeError("Discord rate-limit retry budget exhausted")


def sync_post(channel_id, bot_id, marker, content):
    before = None
    for _ in range(5):
        url = f"/channels/{channel_id}/messages?limit=100"
        if before:
            url += "&before=" + before
        messages = api("GET", url) or []
        for message in messages:
            if (str(message.get("author", {}).get("id")) == str(bot_id)
                    and marker in message.get("content", "")):
                if message["content"] == content:
                    print("[EXISTS] Official bot notice already current.", flush=True)
                    return
                api("PATCH", f"/channels/{channel_id}/messages/{message['id']}",
                    {"content": content, "allowed_mentions": {"parse": []}})
                print("[UPDATED] Existing official bot notice, no duplicates.", flush=True)
                return
        if len(messages) < 100:
            break
        before = str(messages[-1]["id"])
    # Create only when the official bot announcement is genuinely missing.
    api("POST", f"/channels/{channel_id}/messages",
        {"content": content, "allowed_mentions": {"parse": []}})
    print("[CREATED] Official bot notice was missing; added one.", flush=True)


def main():
    if not GID.isdecimal() or not TOKEN:
        raise ValueError("Missing Discord bot GitHub secrets")
    guild = api("GET", f"/guilds/{GID}")
    bot = api("GET", "/users/@me")
    channels = api("GET", f"/guilds/{GID}/channels")
    rules_id = str(guild.get("rules_channel_id") or "")
    channels_by_id = {str(c["id"]): c for c in channels}
    rules = channels_by_id.get(rules_id) if rules_id else None
    if rules is None:
        candidates = [c for c in channels
                      if c.get("type") == 0 and c.get("name") == "rules"]
        if len(candidates) != 1:
            raise RuntimeError("Cannot identify the unique #rules channel.")
        rules = candidates[0]
    welcome = [c for c in channels
               if c.get("type") == 0 and c.get("name") == "welcome"]
    if len(welcome) != 1:
        raise RuntimeError("Cannot identify the unique #welcome channel.")
    print("[CHECK] Syncing official auto-verification instructions", flush=True)
    sync_post(str(rules["id"]), str(bot["id"]), RULE_MARKER, RULES_TEXT)
    sync_post(str(welcome[0]["id"]), str(bot["id"]), WELCOME_MARKER,
              WELCOME_PROMPT)
    print("[DONE] No member, role, category, channel permission or staff changes.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as exc:
        print("FAILED:", exc, file=sys.stderr, flush=True)
        sys.exit(1)
