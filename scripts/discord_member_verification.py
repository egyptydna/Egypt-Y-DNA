#!/usr/bin/env python3
"""Automatic Verified after Discord native Rules Screening (NO manual approval).

Runs on GitHub Actions about every five minutes. Grant Verified only when:
  * Rules Screening is enabled on the existing Egypt Y-DNA server,
  * the Discord guild-member object explicitly has pending == False,
  * the account is human, and
  * the member does not already have Verified.

Guild Members privileged intent is required to LIST members via Discord REST.
A missing 'pending' field is never considered acceptance (fail closed).
This script never alters staff roles or approves members on their behalf.
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
SCREENING_FEATURE = "MEMBER_VERIFICATION_GATE_ENABLED"
ROLE_MANAGEMENT = 1 << 28
ADMINISTRATOR = 1 << 3

def api(method, path, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + path, method=method, data=body,
            headers={
                "Authorization": "Bot " + TOKEN,
                "Content-Type": "application/json",
                "User-Agent": "EgyptYDNAAutoVerification/3.0"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                raw = response.read()
                time.sleep(0.12)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code == 429 and attempt < 5:
                try:
                    pause = min(30, float(json.loads(detail).get("retry_after", 2)))
                except (ValueError, TypeError):
                    pause = 2
                time.sleep(pause + 0.6)
                continue
            if error.code in (401, 403) and "/members?limit=" in path:
                raise RuntimeError(
                    "Cannot list server members. In Discord Developer Portal > "
                    "Egypt YDNA Bot > Bot > Privileged Gateway Intents, enable "
                    "SERVER MEMBERS INTENT, then rerun. "
                    "Discord error: " + detail[:280]) from error
            raise RuntimeError(
                "Discord API " + str(error.code) + " " + method + " " +
                path + ": " + detail[:300]) from error
    raise RuntimeError("Discord API rate limit exceeded retry budget")

def all_members():
    after = None
    for page_no in range(1, 101):
        path = f"/guilds/{GUILD}/members?limit=1000"
        if after:
            path += "&after=" + urllib.parse.quote(after, safe="")
        items = api("GET", path)
        if not isinstance(items, list):
            raise RuntimeError("Discord members endpoint did not return a list")
        for member in items:
            yield member
        if len(items) < 1000:
            return
        after = str(items[-1].get("user", {}).get("id", ""))
        if not after.isdecimal():
            raise RuntimeError("Invalid pagination cursor in Discord member list")
    raise RuntimeError(
        "Server member listing exceeded 100 pages; extend pagination limit "
        "before considering the verification scan complete")

def main():
    if not GUILD.isdecimal() or not TOKEN:
        raise ValueError(
            "GitHub Secrets DISCORD_GUILD_ID and DISCORD_BOT_TOKEN are required")
    guild = api("GET", f"/guilds/{GUILD}")
    print("[CHECK] Server:", guild.get("name"), flush=True)
    if SCREENING_FEATURE not in guild.get("features", []):
        raise RuntimeError(
            "Official Discord Rules Screening is not enabled. Turn it on in "
            "Server Settings > Safety Setup > DM and Spam Protection > "
            "'Members must accept rules before they can talk or DM'. "
            "No one has been verified by this run.")

    roles = api("GET", f"/guilds/{GUILD}/roles")
    by_name = {r["name"].casefold(): r for r in roles}
    verified = by_name.get("verified")
    if not verified:
        raise RuntimeError(
            "The Verified role does not exist. Run the Auto Verification "
            "Setup workflow with apply before scheduling approvals.")

    self_bot = api("GET", "/users/@me")
    me = api("GET", f"/guilds/{GUILD}/members/{self_bot['id']}")
    by_id = {str(r["id"]): r for r in roles}
    mine = {str(x) for x in me.get("roles", [])}
    my_top = max(
        (int(by_id[x]["position"]) for x in mine if x in by_id),
        default=-1)
    if my_top <= int(verified.get("position", 0)):
        raise RuntimeError(
            "Egypt YDNA Bot must be ABOVE Verified in the Discord role hierarchy.")
    my_permissions = int(by_id.get(GUILD, {}).get("permissions", "0"))
    for id_ in mine:
        if id_ in by_id:
            my_permissions |= int(by_id[id_].get("permissions", "0"))
    if not my_permissions & (ROLE_MANAGEMENT | ADMINISTRATOR):
        raise RuntimeError("Egypt YDNA Bot needs Manage Roles.")

    verified_id = str(verified["id"])
    scanned = accepted = pending = missing_pending = bots = already = granted = failures = 0
    for member in all_members():
        user = member.get("user") or {}
        member_id = str(user.get("id", ""))
        if not member_id.isdecimal():
            continue
        scanned += 1
        if user.get("bot"):
            bots += 1
            continue
        if member.get("pending") is True:
            pending += 1
            continue
        # Fail closed: absence/null of "pending" does not prove rule acceptance.
        if member.get("pending") is not False:
            missing_pending += 1
            continue
        accepted += 1
        if verified_id in {str(id_) for id_ in member.get("roles", [])}:
            already += 1
            continue
        try:
            api("PUT",
                f"/guilds/{GUILD}/members/{member_id}/roles/{verified_id}")
            granted += 1
            print("[VERIFIED] Granted role automatically after Rules Screening:",
                  member_id, flush=True)
        except RuntimeError as error:
            failures += 1
            print("[ERROR] Cannot assign Verified to", member_id, error,
                  file=sys.stderr, flush=True)

    print("[SUMMARY] scanned=", scanned, "screening_accepted=", accepted,
          "still_pending=", pending, "pending_unknown=", missing_pending,
          "bots_ignored=", bots, "already_verified=", already,
          "newly_verified=", granted, "errors=", failures, flush=True)
    if missing_pending:
        print("[NOTICE] Members without an explicit pending=false were NOT granted "
              "Verified. Confirm the bot has SERVER MEMBERS INTENT enabled.")
    if failures:
        raise RuntimeError(
            "Some verified-role assignments failed; inspect bot permissions "
            "and Discord's role hierarchy.")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
