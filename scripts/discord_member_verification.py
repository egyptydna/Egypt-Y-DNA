#!/usr/bin/env python3
"""Manual verification by staff reactions, checked by GitHub Actions.

1. A newcomer reads rules, reacts ✅ in #verification, writes a short
   introduction in #verification-chat (no private DNA details).
2. Founder/Administrator/Moderator reacts ✅ to THAT member message.
3. This worker verifies BOTH acknowledgments and assigns Member + Verified.
No staff approval means no access. Bot accounts cannot be approved as humans.
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

GUILD = os.getenv("DISCORD_GUILD_ID", "").strip()
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
BASE = "https://discord.com/api/v10"
RULE_MARKER = "**EGYPT Y-DNA VERIFICATION**"
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
    bot = api("GET", "/users/@me")
    roles = api("GET", f"/guilds/{GUILD}/roles")
    by_name = {r["name"].casefold(): r for r in roles}
    roles_needed = ("member", "verified")
    if any(name not in by_name for name in roles_needed):
        print("SKIP: Create the Verified role using the Verification Room setup first.")
        return
    staff_ids = {str(r["id"]) for r in roles if r["name"].casefold() in STAFF}
    channels = api("GET", f"/guilds/{GUILD}/channels")
    channel_by_name = {c["name"]: c for c in channels if c.get("type") == 0}
    if "verification" not in channel_by_name or "verification-chat" not in channel_by_name:
        print("SKIP: verification/verification-chat channels not yet installed.")
        return
    intro = channel_by_name["verification"]
    applications = channel_by_name["verification-chat"]
    rule_msg = next((m for m in latest_messages(intro["id"], 2)
                     if str(m.get("author", {}).get("id")) == str(bot["id"])
                     and RULE_MARKER in m.get("content", "")), None)
    if not rule_msg:
        print("SKIP: Bot rule-confirmation prompt missing. Run room setup.")
        return
    rule_acceptors = set(people_who_reacted(intro["id"], rule_msg["id"]))
    modlog = channel_by_name.get("mod-log")
    member_cache = {}
    assigned = 0
    approved_messages = 0
    failures = 0
    for message in latest_messages(applications["id"]):
        author = message.get("author", {})
        user_id = str(author.get("id", ""))
        if not user_id or author.get("bot"):
            continue
        if user_id not in rule_acceptors:
            continue
        if not any(r.get("emoji", {}).get("name") == "✅" for r in message.get("reactions", [])):
            continue
        staff_reactors = list(people_who_reacted(applications["id"], message["id"]))
        if not staff_reactors:
            continue
        approved = False
        for reactor_id in staff_reactors:
            if reactor_id == str(guild["owner_id"]):
                approved = True
                break
            if reactor_id not in member_cache:
                member_cache[reactor_id] = api(
                    "GET", f"/guilds/{GUILD}/members/{reactor_id}", optional=True)
            reactor = member_cache[reactor_id]
            if reactor and not reactor.get("pending") and (
                staff_ids.intersection({str(r) for r in reactor.get("roles", [])})
            ):
                approved = True
                break
        if not approved:
            continue
        approved_messages += 1
        if user_id not in member_cache:
            member_cache[user_id] = api("GET", f"/guilds/{GUILD}/members/{user_id}", optional=True)
        applicant = member_cache[user_id]
        if not applicant or applicant.get("pending"):
            continue
        known_roles = {str(role) for role in applicant.get("roles", [])}
        for name in roles_needed:
            role_id = str(by_name[name]["id"])
            if role_id in known_roles:
                continue
            try:
                api("PUT", f"/guilds/{GUILD}/members/{user_id}/roles/{role_id}")
                known_roles.add(role_id)
                assigned += 1
                print("Granted", name, "to", user_id, "after staff approval")
            except RuntimeError as error:
                failures += 1
                print("ERROR approving", user_id, name, error, file=sys.stderr)
        applicant["roles"] = list(known_roles)
        if modlog and str(by_name["verified"]["id"]) in known_roles:
            # Log only upon the newly completed approval, not on every repeat.
            # The above role assignment uses the guarded API calls.
            pass
    print("Applications with staff approval:", approved_messages,
          "| Roles granted:", assigned, "| Failures:", failures)
    if failures:
        raise RuntimeError("One or more approvals failed. Check the bot role hierarchy.")

if __name__ == "__main__":
    try: main()
    except (ValueError, RuntimeError, urllib.error.URLError) as error:
        print("FAILED:", error, file=sys.stderr)
        sys.exit(1)
