#!/usr/bin/env python3
"""Egypt Y-DNA: ✅ on the official #rules message => Verified.

No Discord native rules popup and no moderator approval required.
The scheduled GitHub Action checks every five minutes (subject to GitHub delays).
Only humans who reacted to the bot-owned, designated rules message receive
Verified. Merely joining does NOT grant Verified. Existing roles are preserved.

The bot needs Manage Roles, a role above Verified, and channel permissions to
read messages and reactions in #rules. No privileged Members Intent is needed
for individual Get Guild Member requests in this workflow.
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
RULE_MARKER = "**EGYPT Y-DNA — OFFICIAL SERVER RULES**"
CHECKMARK = "✅"
MANAGE_ROLES = 1 << 28
ADMINISTRATOR = 1 << 3


def api(method, path, data=None, allow_404=False):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    for attempt in range(6):
        request = urllib.request.Request(
            BASE + path, method=method, data=body,
            headers={
                "Authorization": "Bot " + TOKEN,
                "Content-Type": "application/json",
                "User-Agent": "EgyptYDNARulesReactionVerification/4.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read()
                time.sleep(0.13)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            if allow_404 and error.code == 404:
                return None
            if error.code == 429 and attempt < 5:
                try:
                    pause = min(30, float(json.loads(detail).get("retry_after", 2)))
                except (TypeError, ValueError):
                    pause = 2
                time.sleep(pause + 0.5)
                continue
            raise RuntimeError(
                f"Discord HTTP {error.code}: {method} {path}: {detail[:350]}"
            ) from error
    raise RuntimeError("Discord rate-limit retry budget exhausted")


def find_rules_post(guild, bot_id):
    """Use ONLY the server's official rules message; never another user's post."""
    channels = api("GET", f"/guilds/{GUILD}/channels") or []
    text_channels = [
        channel for channel in channels
        if channel.get("type") == 0 and channel.get("name") == "rules"
    ]
    official_id = str(guild.get("rules_channel_id") or "")
    # If Discord configured its official rules channel, that one is authoritative.
    if official_id:
        official = next(
            (c for c in channels if c.get("type") == 0 and
             str(c["id"]) == official_id),
            None,
        )
        if official is None:
            raise RuntimeError(
                "[ACTION REQUIRED] Discord's official rules channel cannot "
                "be found; rerun Rules Cleanup with apply."
            )
        candidates = [official]
    elif len(text_channels) == 1:
        candidates = text_channels
    else:
        raise RuntimeError(
            "[ACTION REQUIRED] Cannot uniquely identify the public #rules "
            "channel. Run Rules Cleanup with apply before verification."
        )

    channel = candidates[0]
    before = None
    # Up to 500 messages; if the one official rules post is missing,
    # deliberately fail closed rather than verify people on join.
    for _ in range(5):
        url = f"/channels/{channel['id']}/messages?limit=100"
        if before:
            url += "&before=" + before
        batch = api("GET", url) or []
        for message in batch:
            if (str(message.get("author", {}).get("id")) == str(bot_id)
                    and RULE_MARKER in message.get("content", "")):
                return channel, message
        if len(batch) < 100:
            break
        before = str(batch[-1]["id"])
    raise RuntimeError(
        "[ACTION REQUIRED] No official bot-authored rules message found "
        "in #rules. Run Rules Cleanup with apply to post and seed ✅."
    )


def accepted_users(channel_id, message_id):
    """Paginate reactions: never confuse the bot's seeded ✅ with a member."""
    after = None
    emoji = urllib.parse.quote(CHECKMARK, safe="")
    for _ in range(200):
        url = (
            f"/channels/{channel_id}/messages/{message_id}"
            f"/reactions/{emoji}?limit=100"
        )
        if after:
            url += "&after=" + urllib.parse.quote(after, safe="")
        users = api("GET", url) or []
        for user in users:
            if not user.get("bot"):
                yield str(user["id"])
        if len(users) < 100:
            return
        after = str(users[-1]["id"])
    raise RuntimeError("More than 20,000 rule acknowledgements; pagination limit reached")


def main():
    if not GUILD.isdecimal() or not TOKEN:
        raise ValueError("Missing DISCORD_GUILD_ID / DISCORD_BOT_TOKEN secrets")

    guild = api("GET", f"/guilds/{GUILD}")
    roles = api("GET", f"/guilds/{GUILD}/roles")
    by_name = {r["name"].casefold(): r for r in roles}
    verified = by_name.get("verified")
    if not verified:
        raise RuntimeError("[ACTION REQUIRED] Verified role missing.")
    bot = api("GET", "/users/@me")
    bot_member = api("GET", f"/guilds/{GUILD}/members/{bot['id']}")
    by_id = {str(r["id"]): r for r in roles}
    top = max(
        (int(by_id[str(r)]["position"]) for r in bot_member.get("roles", [])
         if str(r) in by_id),
        default=-1,
    )
    if top <= int(verified["position"]):
        raise RuntimeError(
            "[ACTION REQUIRED] Egypt YDNA Bot role must be ABOVE Verified."
        )
    permissions = int(by_id.get(GUILD, {}).get("permissions", "0"))
    for rid in bot_member.get("roles", []):
        if str(rid) in by_id:
            permissions |= int(by_id[str(rid)].get("permissions", "0"))
    if not permissions & (MANAGE_ROLES | ADMINISTRATOR):
        raise RuntimeError("[ACTION REQUIRED] Egypt YDNA Bot needs Manage Roles.")

    channel, message = find_rules_post(guild, bot["id"])
    print("[CHECK] #rules id:", channel["id"], "message:", message["id"])
    if not any(
        r.get("emoji", {}).get("name") == CHECKMARK
        for r in message.get("reactions", [])
    ):
        raise RuntimeError(
            "[ACTION REQUIRED] No ✅ under the official rules message. "
            "Run Rules Cleanup with apply to add it."
        )

    seen = checked = pending = already = granted = missing = failures = 0
    verified_id = str(verified["id"])
    for user_id in accepted_users(channel["id"], message["id"]):
        seen += 1
        member = api("GET", f"/guilds/{GUILD}/members/{user_id}", allow_404=True)
        if not member:
            missing += 1  # Person has left the server.
            continue
        checked += 1
        if member.get("user", {}).get("bot"):
            continue
        if member.get("pending", False) is not False:
            pending += 1
            continue
        if verified_id in {str(r) for r in member.get("roles", [])}:
            already += 1
            continue
        try:
            api("PUT", f"/guilds/{GUILD}/members/{user_id}/roles/{verified_id}")
            granted += 1
            print("[VERIFIED] ✅ rules accepted by", user_id, flush=True)
        except RuntimeError as error:
            failures += 1
            print("[ERROR] Could not assign Verified:", user_id, error,
                  file=sys.stderr, flush=True)

    print("[SUMMARY] reactions=", seen, "members_found=", checked,
          "pending=", pending, "already_verified=", already,
          "newly_verified=", granted, "left_server=", missing,
          "errors=", failures, flush=True)
    if failures:
        raise RuntimeError("Some ✅ approvals failed; check Discord role hierarchy.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr, flush=True)
        sys.exit(1)
