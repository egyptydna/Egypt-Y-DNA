#!/usr/bin/env python3
"""Automatically grant Verified to human Discord members without a rules popup.

The owner chose to disable native Rules Screening. On each scheduled GitHub
Actions run, assign Verified to joined human accounts without staff approval.
Bot accounts are never granted Verified. A genuinely pending member is skipped.
Requires Server Members Intent to list members and Manage Roles to add Verified.
The private STAFF category is still protected by channel permissions.
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
    print("[MODE] Automatic Verified on server join; no native rules popup "
          "or moderator review required.", flush=True)
    if "MEMBER_VERIFICATION_GATE_ENABLED" in guild.get("features", []):
        print("[NOTICE] Native Rules Screening is currently enabled in Discord. "
              "Members still pending its acceptance will be skipped. "
              "Disable it in Discord settings if you want no popup.", flush=True)

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
    scanned = eligible = pending = unknown_pending = bots = already = granted = failures = 0
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
        # Treat missing pending as False per Discord API. Explicit null or
        # invalid statuses are ambiguous and fail closed. When Screening is
        # disabled, joined users should not be pending.
        if member.get("pending", False) is not False:
            unknown_pending += 1
            continue
        eligible += 1
        if verified_id in {str(id_) for id_ in member.get("roles", [])}:
            already += 1
            continue
        try:
            api("PUT",
                f"/guilds/{GUILD}/members/{member_id}/roles/{verified_id}")
            granted += 1
            print("[VERIFIED] Granted role automatically after joining server:",
                  member_id, flush=True)
        except RuntimeError as error:
            failures += 1
            print("[ERROR] Cannot assign Verified to", member_id, error,
                  file=sys.stderr, flush=True)

    print("[SUMMARY] scanned=", scanned, "eligible_joined_members=", eligible,
          "still_pending=", pending, "pending_unknown=", unknown_pending,
          "bots_ignored=", bots, "already_verified=", already,
          "newly_verified=", granted, "errors=", failures, flush=True)
    if unknown_pending:
        print("[NOTICE] Members whose pending status was null or invalid were "
              "not automatically Verified; they need a valid Discord member status.")
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
