#!/usr/bin/env python3
"""Safely rename only the legacy exact-named 'E' Discord role.

Why: Discord mobile may autocomplete a role named @E when the owner tries
to type @everyone, producing an @E mention followed by plain text "veryone".

Does not delete any role, change role IDs/assignments, alter permissions,
change channel overwrites or affect the actual @everyone role.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

GID = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
MODE = os.getenv("MODE", "preview").strip().lower()
BASE = "https://discord.com/api/v10"
OLD_NAME = "E"
NEW_NAME = "Legacy Y-DNA E"
MANAGE_ROLES = 1 << 28
ADMIN = 1 << 3


def api(method, path, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        request = urllib.request.Request(
            BASE + path, data=body, method=method,
            headers={
                "Authorization": "Bot " + TOKEN,
                "Content-Type": "application/json",
                "User-Agent": "EgyptYDNAEveryoneMentionFix/1.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read()
                time.sleep(0.12)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code == 429 and attempt < 5:
                try:
                    delay = min(30, float(json.loads(detail).get("retry_after", 2)))
                except (ValueError, TypeError):
                    delay = 2
                time.sleep(delay + 0.5)
                continue
            raise RuntimeError(
                f"Discord HTTP {error.code} {method} {path}: {detail[:350]}"
            ) from error
    raise RuntimeError("Discord API rate-limit retries exhausted")


def target_role(roles):
    matches = [role for role in roles if role.get("name") == OLD_NAME]
    if len(matches) > 1:
        raise RuntimeError("More than one exact E role; no changes made.")
    if not matches:
        print("[ALREADY] No role named E. Nothing to rename.", flush=True)
        return None
    role = matches[0]
    if role.get("managed"):
        raise RuntimeError("Legacy E is a managed integration role; cannot rename.")
    if any(r.get("name").casefold() == NEW_NAME.casefold() for r in roles):
        raise RuntimeError(
            "A role named Legacy Y-DNA E already exists alongside E. "
            "No duplicate names created and no role changed."
        )
    return role


def main():
    if MODE not in ("preview", "apply"):
        raise ValueError("MODE must be preview or apply")
    if not GID.isdecimal() or not TOKEN:
        raise ValueError("Missing DISCORD_GUILD_ID or DISCORD_BOT_TOKEN")

    guild = api("GET", f"/guilds/{GID}")
    if str(guild.get("id", GID)) != GID:
        raise RuntimeError("Guild ID mismatch; no changes made.")
    roles = api("GET", f"/guilds/{GID}/roles")
    legacy = target_role(roles)
    if legacy is None:
        return
    print("[FOUND] Server:", guild.get("name"),
          "| problematic role:", OLD_NAME,
          "| ID:", legacy["id"],
          "| mode:", MODE, flush=True)

    bot = api("GET", "/users/@me")
    member = api("GET", f"/guilds/{GID}/members/{bot['id']}")
    by_id = {str(role["id"]): role for role in roles}
    top = max(
        (int(by_id[str(rid)]["position"]) for rid in member.get("roles", [])
         if str(rid) in by_id),
        default=-1,
    )
    permissions = int(by_id.get(GID, {}).get("permissions", "0"))
    for rid in member.get("roles", []):
        if str(rid) in by_id:
            permissions |= int(by_id[str(rid)].get("permissions", "0"))
    if not (permissions & (MANAGE_ROLES | ADMIN)):
        raise RuntimeError(
            "[OWNER ACTION] Bot lacks Manage Roles. Rename the E role "
            "manually via Server Settings > Roles > E > Edit Role."
        )
    if int(legacy.get("position", 0)) >= top:
        raise RuntimeError(
            "[OWNER ACTION] Legacy E role is at or above the bot. "
            "Rename it in Server Settings > Roles. "
            f"Bot position={top}; E position={legacy['position']}."
        )

    if MODE == "preview":
        print("[PREVIEW] Rename the EXISTING role E to", NEW_NAME,
              "without changing role ID, permissions, order, member assignments "
              "or other roles. Nothing changed yet.", flush=True)
        return

    api("PATCH", f"/guilds/{GID}/roles/{legacy['id']}",
        {"name": NEW_NAME})
    updated_roles = api("GET", f"/guilds/{GID}/roles")
    updated = next(
        (r for r in updated_roles if str(r["id"]) == str(legacy["id"])), None
    )
    if not updated or updated.get("name") != NEW_NAME:
        raise RuntimeError("Discord did not confirm the role rename.")
    if (int(updated.get("permissions", "0")) !=
            int(legacy.get("permissions", "0"))):
        raise RuntimeError("Discord changed role permissions unexpectedly. Review manually.")
    print("[SUCCESS] Renamed E to", NEW_NAME,
          "| preserved role ID:", legacy["id"],
          "| no member role assignments changed. Test a NEW @everyone message.",
          flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
