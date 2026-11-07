#!/usr/bin/env python3
"""Automatically label Discord bot accounts with the neutral Bot role.

Runs on the scheduled GitHub verification workflow. The Discord bot itself
is always checked even if the server has not enabled Server Members Intent.
To label OTHER bots, enable Server Members Intent on the Discord developer
portal for this application. Only accounts user.bot == True are labeled.
Never assigns human membership privileges or staff roles to bots.
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

def api(method, path, data=None, optional=False):
    raw = json.dumps(data).encode() if data is not None else None
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + path, data=raw, method=method,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNABotLabeller/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                body = response.read()
                time.sleep(0.12)
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            if error.code == 429 and attempt < 5:
                try: pause = min(30, float(json.loads(detail).get("retry_after", 2)))
                except (ValueError, TypeError): pause = 2
                time.sleep(pause + 0.5)
                continue
            if optional and error.code in (401, 403):
                print("NOTE: Member listing is unavailable. Enable Server Members Intent "
                      "for the bot in Discord Developer Portal > Bot, then rerun. "
                      "The existing Egypt YDNA Bot is still labeled.", flush=True)
                return None
            raise RuntimeError(f"Discord {error.code} {method} {path}: {detail[:250]}")
    raise RuntimeError("Rate-limit retry limit exceeded")

def main():
    if not GUILD.isdecimal() or not TOKEN:
        raise ValueError("Missing DISCORD_GUILD_ID / DISCORD_BOT_TOKEN")
    roles = api("GET", f"/guilds/{GUILD}/roles")
    bot_role = next((r for r in roles if r.get("name") == "Bot"), None)
    if not bot_role:
        print("SKIP: Bot role not installed. Run Verification Category Setup.")
        return
    self_bot = api("GET", "/users/@me")
    checked = granted = 0
    def grant_bot(member):
        nonlocal checked, granted
        user = member.get("user") or {}
        if not user.get("bot"):
            return
        checked += 1
        member_id = str(user["id"])
        if str(bot_role["id"]) in {str(r) for r in member.get("roles", [])}:
            return
        api("PUT", f"/guilds/{GUILD}/members/{member_id}/roles/{bot_role['id']}")
        granted += 1
        print("[BOT ROLE]", member_id, flush=True)

    own_member = api("GET", f"/guilds/{GUILD}/members/{self_bot['id']}")
    grant_bot(own_member)

    # Member list requests require the application's privileged Members Intent.
    after = None
    while True:
        endpoint = f"/guilds/{GUILD}/members?limit=1000"
        if after:
            endpoint += "&after=" + urllib.parse.quote(after, safe="")
        entries = api("GET", endpoint, optional=True)
        if entries is None:
            break
        for member in entries:
            grant_bot(member)
        if len(entries) < 1000:
            break
        after = str(entries[-1]["user"]["id"])
    print(f"DONE: bot members checked={checked}, newly labeled={granted}")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr)
        sys.exit(1)
