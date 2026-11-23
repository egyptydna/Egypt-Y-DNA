#!/usr/bin/env python3
"""Read-only Discord audit of member removal for Egypt Y-DNA.

No writes to Discord. Print aggregated actor information only, no member IDs,
member names, user IDs, raw audit-log reasons or raw audit entries.
Public GitHub Actions logs must not expose affected users' personal information.
"""
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

BASE = "https://discord.com/api/v10"
TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
GID = os.environ.get("DISCORD_GUILD_ID", "").strip()
EVENTS = {20: "member_kick", 21: "member_prune", 22: "member_ban"}
DISCORD_EPOCH_MS = 1420070400000
LOOKBACK_DAYS = 7


def get(path):
    request = urllib.request.Request(
        BASE + path, method="GET",
        headers={"Authorization": "Bot " + TOKEN,
                 "User-Agent": "EgyptYDNAMemberRemovalAudit/1.0"},
    )
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            message = error.read().decode("utf-8", "replace")
            if error.code == 429 and attempt < 4:
                try:
                    backoff = min(30, float(json.loads(message).get("retry_after", 2)))
                except (ValueError, TypeError):
                    backoff = 2
                time.sleep(backoff + 0.5)
                continue
            if error.code == 403:
                raise RuntimeError(
                    "Discord denied audit log access (HTTP 403). "
                    "Give Egypt YDNA Bot 'View Audit Log' or inspect audit in Discord manually."
                ) from error
            raise RuntimeError(
                f"Discord audit GET failed with HTTP {error.code}"
            ) from error
    raise RuntimeError("Rate limit exceeded")


def entry_time(entry):
    try:
        ident = int(entry["id"])
        epoch_ms = (ident >> 22) + DISCORD_EPOCH_MS
        return dt.datetime.fromtimestamp(epoch_ms / 1000, dt.timezone.utc)
    except (TypeError, KeyError, ValueError, OverflowError):
        return None


def actor_label(entry, users):
    actor = users.get(str(entry.get("user_id")), {})
    if actor.get("bot"):
        # Bot username is visible publicly in the server; do not print IDs.
        return "bot: " + str(actor.get("username", "unknown bot"))[:40]
    if actor:
        return "human staff (check private Discord audit log)"
    return "unknown actor (check private Discord audit log)"


def reason_class(entry):
    reason = str(entry.get("reason") or "").casefold()
    if re.search(r"unverif|not verif|verification|captcha|verify|failed rules", reason):
        return "verification-related reason"
    if re.search(r"prune|inactiv|raid|suspicious|security", reason):
        return "inactivity/raid/security-related reason"
    return "reason unavailable or not specifically classified"


def main():
    if not GID.isdecimal() or not TOKEN:
        raise RuntimeError("Missing DISCORD_GUILD_ID / DISCORD_BOT_TOKEN")
    guild = get(f"/guilds/{GID}")
    name = str(guild.get("name", "server"))
    now = dt.datetime.now(dt.timezone.utc)
    since = now - dt.timedelta(days=LOOKBACK_DAYS)
    print("[AUDIT] Server:", name, "| window:", since.isoformat(timespec="seconds"),
          "to", now.isoformat(timespec="seconds"), flush=True)

    total_count = 0
    for event_id, event_label in EVENTS.items():
        # Discord returns the latest matching entries, up to 100. Audit logs
        # show actual moderation events, not voluntary member departures.
        data = get(f"/guilds/{GID}/audit-logs?action_type={event_id}&limit=100")
        users = {str(u["id"]): u for u in data.get("users", []) if "id" in u}
        entries = [
            e for e in data.get("audit_log_entries", [])
            if entry_time(e) is not None and entry_time(e) >= since
        ]
        total_count += len(entries)
        summary = Counter((actor_label(e, users), reason_class(e)) for e in entries)
        print(f"[{event_label.upper()}] entries in past {LOOKBACK_DAYS}d: {len(entries)}",
              flush=True)
        for (actor, category), count in summary.most_common():
            print(f"  count={count} | actor={actor} | {category}", flush=True)
        if len(data.get("audit_log_entries", [])) == 100:
            print("  [LIMIT] Most recent 100 events checked; older events omitted.")
    if total_count == 0:
        print("[SUMMARY] No kick, prune or ban audit entries in checked window. "
              "Members may have left voluntarily or been removed by another mechanism; "
              "absence of audit entries does not establish why an individual left.",
              flush=True)
    else:
        print("[SUMMARY] Checked actual kick/prune/ban actions; "
              "see categories above. Nothing on Discord was changed.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, urllib.error.URLError) as exc:
        print("AUDIT UNAVAILABLE:", exc, file=sys.stderr, flush=True)
        sys.exit(1)
