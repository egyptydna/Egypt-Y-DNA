#!/usr/bin/env python3
"""Assign or remove a privileged Discord role ONLY via repo owner's workflow.

Founder is capped at two people INCLUDING the guild owner, whether or not
they wear the Founder badge. Discord itself cannot enforce that cap if
the server owner adds the role manually outside this workflow.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

GID = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
ACTOR = os.getenv("GITHUB_ACTOR", "")
ROLE = os.getenv("STAFF_ROLE", "").strip()
TARGET = os.getenv("TARGET_USER_ID", "").strip()
OP = os.getenv("OPERATION", "").strip()
BASE = "https://discord.com/api/v10"

def api(method, path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    for attempt in range(6):
        req = urllib.request.Request(
            BASE + path, data=payload, method=method,
            headers={"Authorization": "Bot " + TOKEN,
                     "Content-Type": "application/json",
                     "User-Agent": "EgyptYDNAOwnerStaffAssignment/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                content = response.read()
                time.sleep(0.2)
                return json.loads(content) if content else None
        except urllib.error.HTTPError as error:
            message = error.read().decode(errors="replace")
            if error.code == 429 and attempt < 5:
                try: delay = min(30, float(json.loads(message).get("retry_after", 2)))
                except (ValueError, TypeError): delay = 2
                time.sleep(delay + 0.5)
                continue
            raise RuntimeError(f"Discord HTTP {error.code}: {message[:300]}")
    raise RuntimeError("Discord API rate limit retries exhausted")

def main():
    if ACTOR.casefold() != "egyptydna":
        raise RuntimeError("Only the repository owner @egyptydna can assign staff roles")
    if ROLE not in ("Founder", "Administrator", "Moderator"):
        raise ValueError("Only Founder, Administrator, Moderator permitted")
    if OP not in ("assign", "remove") or not GID.isdecimal() or not TARGET.isdecimal():
        raise ValueError("Invalid action, target user ID or guild ID")
    if not TOKEN:
        raise ValueError("Missing DISCORD_BOT_TOKEN secret")
    guild = api("GET", f"/guilds/{GID}")
    roles = api("GET", f"/guilds/{GID}/roles")
    desired = next((r for r in roles if r["name"] == ROLE), None)
    if not desired:
        raise RuntimeError("Target staff role not found. Run staff-roles setup first.")
    target = api("GET", f"/guilds/{GID}/members/{TARGET}")
    assigned_already = str(desired["id"]) in [str(r) for r in target.get("roles", [])]
    if OP == "assign" and assigned_already:
        print("No change: user already holds " + ROLE)
        return
    if OP == "remove" and not assigned_already:
        print("No change: user does not hold " + ROLE)
        return

    if OP == "assign" and ROLE == "Founder":
        counts = api("GET", f"/guilds/{GID}/roles/member-counts")
        owner = str(guild["owner_id"])
        owner_member = api("GET", f"/guilds/{GID}/members/{owner}")
        owner_holds = str(desired["id"]) in [str(r) for r in owner_member.get("roles", [])]
        existing_count = int(counts.get(str(desired["id"]), 0))
        # Count the permanent owner even if they haven't added the badge.
        count_people_before = existing_count + (0 if owner_holds else 1)
        count_after = count_people_before if TARGET == owner else count_people_before + 1
        if count_after > 2:
            raise RuntimeError(
                "Founder cap reached: at most TWO people including the server owner. "
                f"Current badge holders={existing_count}; owner_has_badge={owner_holds}."
            )
        print(f"Founder count check OK: {count_people_before} -> {count_after}")

    method = "PUT" if OP == "assign" else "DELETE"
    api(method, f"/guilds/{GID}/members/{TARGET}/roles/{desired['id']}")
    print(f"SUCCESS: {OP} {ROLE} for Discord member {TARGET}")

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as exc:
        print("FAILED:", exc, file=sys.stderr)
        sys.exit(1)
