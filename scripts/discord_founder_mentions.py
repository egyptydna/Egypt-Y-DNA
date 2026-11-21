#!/usr/bin/env python3
"""Give only the existing trusted Founder role Discord's Mention Everyone permission.

This permits @everyone, @here and pinging otherwise unmentionable roles.
Does NOT modify @everyone, Verified, geographic/Y-DNA roles, staff assignments,
role order, message contents or channel/category overwrites.
Use MODE=preview before MODE=apply. Server owner can already mass-mention.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

GID = os.environ.get("DISCORD_GUILD_ID", "").strip()
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
MODE = os.environ.get("MODE", "preview").strip()
BASE = "https://discord.com/api/v10"
MENTION_EVERYONE = 1 << 17
MANAGE_ROLES = 1 << 28
ADMINISTRATOR = 1 << 3


def api(method, endpoint, data=None):
    payload = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        request = urllib.request.Request(
            BASE + endpoint, method=method, data=payload,
            headers={
                "Authorization": "Bot " + TOKEN,
                "Content-Type": "application/json",
                "User-Agent": "EgyptYDNAFounderMentions/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read()
                time.sleep(0.15)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            if error.code == 429 and attempt < 5:
                try:
                    delay = min(30, float(json.loads(detail).get("retry_after", 2)))
                except (TypeError, ValueError):
                    delay = 2
                time.sleep(delay + 0.5)
                continue
            raise RuntimeError(
                f"Discord HTTP {error.code} {method} {endpoint}: {detail[:260]}"
            ) from error
    raise RuntimeError("Rate limit retries exhausted")


def main():
    if MODE not in ("preview", "apply"):
        raise ValueError("MODE must be preview or apply")
    if not GID.isdecimal() or not TOKEN:
        raise ValueError("Missing GitHub DISCORD_GUILD_ID or DISCORD_BOT_TOKEN")
    guild = api("GET", f"/guilds/{GID}")
    roles = api("GET", f"/guilds/{GID}/roles")
    founders = [role for role in roles if role["name"].casefold() == "founder"]
    if len(founders) != 1:
        raise RuntimeError("Exactly one Founder role required; no changes made.")
    target = founders[0]
    if target.get("managed"):
        raise RuntimeError("Founder role is managed and cannot be edited.")
    old = int(target.get("permissions", "0"))
    wanted = old | MENTION_EVERYONE
    print("[CHECK] Server", guild.get("name"), "| role", target["name"],
          "| mention everyone:", bool(old & MENTION_EVERYONE), flush=True)
    if wanted == old:
        print("[EXISTS] Founder already has permission. "
              "If Discord suggests @E, type @everyone COMPLETELY and do "
              "not tap the unrelated @E role suggestion.", flush=True)
        return

    bot = api("GET", "/users/@me")
    member = api("GET", f"/guilds/{GID}/members/{bot['id']}")
    by_id = {str(role["id"]): role for role in roles}
    bot_perms = int(by_id.get(GID, {}).get("permissions", "0"))
    for rid in member.get("roles", []):
        bot_perms |= int(by_id.get(str(rid), {}).get("permissions", "0"))
    bot_top = max(
        (int(by_id[str(rid)]["position"]) for rid in member.get("roles", [])
         if str(rid) in by_id),
        default=-1,
    )
    if bot_top <= int(target.get("position", 0)) or not (
        bot_perms & (MANAGE_ROLES | ADMINISTRATOR)
    ):
        raise RuntimeError(
            "[OWNER ACTION REQUIRED] Egypt YDNA Bot cannot edit the Founder "
            "role due to role hierarchy or missing Manage Roles. As owner, "
            "open Discord > Server Settings > Roles > Founder > Permissions; "
            "enable 'Mention @everyone, @here, and All Roles' there. "
            "Do not give the privilege to @everyone."
        )
    if MODE == "preview":
        print("[PREVIEW] Only add Mention Everyone to Founder, preserving "
              "all other current Founder permissions. No Discord changes.")
        return

    api("PATCH", f"/guilds/{GID}/roles/{target['id']}",
        {"permissions": str(wanted)})
    confirm = api("GET", f"/guilds/{GID}/roles")
    confirmed = next(
        (role for role in confirm if str(role["id"]) == str(target["id"])),
        None,
    )
    if not confirmed or not int(confirmed.get("permissions", "0")) & MENTION_EVERYONE:
        raise RuntimeError("Discord did not confirm Founder mention permission.")
    print("[APPLIED] Founder can now ping @everyone, @here and all roles. "
          "Regular members are unchanged; type the FULL @everyone, not @E.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
