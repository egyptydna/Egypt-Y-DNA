#!/usr/bin/env python3
"""Manual verification by staff reactions, checked by GitHub Actions.

1. A newcomer accepts the mandatory Discord Rules Screening checkbox.
2. They write a short introduction in #verification-chat (no private DNA details).
3. Founder/Administrator/Moderator reacts ✅ to THAT applicant's message.
4. This worker requires both native screening completion and staff approval.
No staff approval means no access. Bot accounts cannot be approved as humans.
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
BASE = "https://discord.com/api/v10"
EMOJI = urllib.parse.quote("✅", safe="")
STAFF = {"founder", "administrator", "moderator"}

def api(method, path, data=None, optional=False):
    body = json.dumps(data).encode() if data is not None else None
    for attempt in range(6):
        req = urllib.request.Request(BASE + path, data=body, method=method, headers={
            "Authorization": "Bot " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "EgyptYDNAManualVerification/2.0"
        })
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                raw = res.read()
                time.sleep(0.16)
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            text = error.read().decode(errors="replace")
            if error.code == 429 and attempt < 5:
                try: delay = min(30, float(json.loads(text).get("retry_after", 2)))
                except (TypeError, ValueError): delay = 2
                time.sleep(delay + 0.5)
                continue
            if error.code == 404 and optional:
                return None
            raise RuntimeError(f"Discord HTTP {error.code} {method} {path}: {text[:350]}")
    raise RuntimeError("Rate limit retries exhausted")

def people_who_reacted(channel_id, message_id, emoji=EMOJI):
    after = None
    while True:
        path = f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}?limit=100"
        if after: path += "&after=" + urllib.parse.quote(after, safe="")
        people = api("GET", path, optional=True) or []
        for user in people:
            if not user.get("bot"):
                yield str(user["id"])
        if len(people) < 100:
            return
        after = str(people[-1]["id"])

def latest_messages(channel_id, max_pages=10):
    before = None
    for _ in range(max_pages):
        path = f"/channels/{channel_id}/messages?limit=100"
        if before: path += "&before=" + before
        batch = api("GET", path) or []
        for msg in batch:
            yield msg
        if len(batch) < 100:
            break
        before = str(batch[-1]["id"])

def main():
    if not GUILD.isdecimal() or not TOKEN:
        raise ValueError("Missing GitHub Secrets DISCORD_GUILD_ID / DISCORD_BOT_TOKEN")
    guild = api("GET", f"/guilds/{GUILD}")
    # No automatic Verified role can be issued unless Discord's official rules
    # checkbox is enabled. This prevents an emoji reaction from substituting
    # for the native membership-screening acceptance.
    if "MEMBER_VERIFICATION_GATE_ENABLED" not in guild.get("features", []):
        print("[ACTION REQUIRED] Native Discord Rules Screening is disabled. "
              "Enable in Server Settings > Safety Setup > DM and Spam Protection. "
              "No Verified roles will be issued until it is enabled.")
        return

    roles = api("GET", f"/guilds/{GUILD}/roles")
    by_name = {r["name"].casefold(): r for r in roles}
    verified = by_name.get("verified")
    if not verified:
        print("SKIP: Create the Verified role using Verification Setup first.")
        return
    staff_ids = {str(r["id"]) for r in roles if r["name"].casefold() in STAFF}
    channels = api("GET", f"/guilds/{GUILD}/channels")
    applications = next((c for c in channels if c.get("type") == 0
                         and c["name"] == "verification-chat"), None)
    if not applications:
        print("SKIP: #verification-chat is missing.")
        return
    modlog = next((c for c in channels if c.get("type") == 0
                   and c["name"] == "mod-log"), None)
    cache = {}
    verified_count = 0
    applications_approved = 0
    errors = 0
    for message in latest_messages(applications["id"]):
        author = message.get("author", {})
        user_id = str(author.get("id", ""))
        if not user_id or author.get("bot"):
            continue
        if not any(r.get("emoji", {}).get("name") == "✅"
                   for r in message.get("reactions", [])):
            continue
        staff_reactors = list(people_who_reacted(applications["id"], message["id"]))
        if not staff_reactors:
            continue
        approved = False
        for reactor_id in staff_reactors:
            if reactor_id == str(guild["owner_id"]):
                approved = True
                break
            if reactor_id not in cache:
                cache[reactor_id] = api(
                    "GET", f"/guilds/{GUILD}/members/{reactor_id}", optional=True)
            moderator = cache[reactor_id]
            if moderator and not moderator.get("pending") and (
                staff_ids.intersection({str(r) for r in moderator.get("roles", [])})
            ):
                approved = True
                break
        if not approved:
            continue
        applications_approved += 1
        if user_id not in cache:
            cache[user_id] = api(
                "GET", f"/guilds/{GUILD}/members/{user_id}", optional=True)
        applicant = cache[user_id]
        if not applicant or applicant.get("pending"):
            # A pending member has NOT accepted the native Discord checkbox.
            continue
        if str(verified["id"]) in {str(role) for role in applicant.get("roles", [])}:
            continue
        try:
            api("PUT",
                f"/guilds/{GUILD}/members/{user_id}/roles/{verified['id']}")
            applicant.setdefault("roles", []).append(str(verified["id"]))
            verified_count += 1
            print("[VERIFIED] Staff approved", user_id,
                  "and native rules checkbox was completed")
            if modlog:
                try:
                    api("POST", f"/channels/{modlog['id']}/messages", {
                        "content": "✅ Staff verified <@" + user_id +
                                   "> after accepting Discord's rules checkbox.",
                        "allowed_mentions": {"parse": []}
                    })
                except RuntimeError as error:
                    print("[NOTICE] Could not post moderation log:", error)
        except RuntimeError as error:
            errors += 1
            print("[ERROR] Granting Verified to", user_id, error, file=sys.stderr)
    print("Completed: staff-approved posts:", applications_approved,
          "| newly Verified:", verified_count, "| errors:", errors)
    if errors:
        raise RuntimeError(
            "Some approvals failed. Check bot role hierarchy and Manage Roles.")

if __name__ == "__main__":
    try: main()
    except (ValueError, RuntimeError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr)
        sys.exit(1)
