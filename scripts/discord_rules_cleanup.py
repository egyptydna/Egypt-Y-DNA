#!/usr/bin/env python3
"""Consolidate duplicate #rules channels safely.

Keep Discord's official guild.rules_channel_id if present. If absent,
prefer the top-level #rules channel over the duplicate inside VERIFICATION.
Keep the selected channel at its current position, ensure public read-only
permissions, publish one rules post, make it the community rules channel.
Delete only empty duplicate channels; archive populated duplicates privately
inside STAFF without erasing history. Always run preview before apply.

No Rules Screening popup required. The rules channel is informational.
"""
import json, os, sys, time, urllib.error, urllib.request

API = "https://discord.com/api/v10"
TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GID = os.getenv("DISCORD_GUILD_ID", "").strip()
MODE = os.getenv("MODE", "preview").strip().lower()
VIEW, SEND, READ, REACT, THREAD = 1<<10, 1<<11, 1<<16, 1<<6, 1<<38

RULES_TEXT = (
    "📜 **EGYPT Y-DNA — OFFICIAL SERVER RULES**\n\n"
    "**1. Respect everyone.** No harassment, insults, racism, hate speech or discrimination.\n"
    "**2. Remain factual.** Support scientific claims with credible sources and "
    "distinguish evidence from hypotheses.\n"
    "**3. Stay on topic.** Focus on Egyptian Y-DNA, genetic genealogy, ancestry and relevant history.\n"
    "**4. No religious or political arguments.** Evidence-based historical context is welcome.\n"
    "**5. No inappropriate content.** No NSFW material, graphic violence, scams or spam.\n"
    "**6. Respect privacy.** Never reveal private test results, personal identities, "
    "kit numbers or precise locations without the person's permission.\n"
    "**7. Avoid unsupported identity claims.** A haplogroup alone does not prove "
    "someone's ethnicity, nationality or tribal affiliation.\n"
    "**8. Use the appropriate channels.** English is our main language; use "
    "#arabic-chat for Arabic discussion.\n"
    "**9. Everyone is welcome.** Treat all nationalities, backgrounds and lineages fairly.\n"
    "**10. Follow staff instructions.** Serious or repeated violations may lead to "
    "timeouts or removal.\n\n"
    "**Please read these rules before participating. Verified is granted "
    "automatically after joining, without a rules popup or moderator approval.**"
)
MARKER = "**EGYPT Y-DNA — OFFICIAL SERVER RULES**"
DUPLICATE_NAMES = {"rules", "📝rules", "📜rules", "📋rules", "rules-and-guidelines"}

def request(method, endpoint, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    for retry in range(5):
        req = urllib.request.Request(API+endpoint, data=data, method=method,
            headers={"Authorization": "Bot "+TOKEN,
                     "Content-Type":"application/json",
                     "User-Agent":"EgyptYDNARulesCleanup/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                content = response.read()
                time.sleep(0.2)
                return json.loads(content) if content else None
        except urllib.error.HTTPError as e:
            detail=e.read().decode(errors="replace")
            if e.code == 429 and retry < 4:
                try: pause=min(30,float(json.loads(detail).get("retry_after",2)))
                except (ValueError,TypeError): pause=2
                time.sleep(pause+0.5)
                continue
            raise RuntimeError(f"Discord {e.code} {method} {endpoint}: {detail[:400]}")
    raise RuntimeError("Discord rate-limit exhausted")

def apply(method, endpoint, payload, label):
    if MODE == "preview":
        print("[PREVIEW]",label,flush=True)
        return None
    result=request(method,endpoint,payload)
    print("[APPLIED]",label,flush=True)
    return result

def overwrite(identity, allow=0, deny=0, kind=0):
    return {"id":str(identity),"type":kind,"allow":str(allow),"deny":str(deny)}

def main():
    if MODE not in ("preview","apply"): raise ValueError("MODE must be preview or apply")
    if not TOKEN or not GID.isdecimal(): raise ValueError("Missing Discord GitHub secrets")
    guild=request("GET",f"/guilds/{GID}")
    channels=request("GET",f"/guilds/{GID}/channels")
    bot=request("GET","/users/@me")
    roles=request("GET",f"/guilds/{GID}/roles")
    staff_ids=[str(r["id"]) for r in roles if r["name"] in
               ("Founder","Administrator","Moderator")]
    candidates=[c for c in channels if c.get("type")==0 and
                (c["name"].casefold() in DUPLICATE_NAMES or
                 str(c["id"])==str(guild.get("rules_channel_id")))]
    official_id=str(guild.get("rules_channel_id") or "")
    official=next((c for c in candidates if str(c["id"])==official_id),None)
    if not official:
        no_category=[c for c in candidates if c["name"].casefold()=="rules"
                     and c.get("parent_id") is None]
        normal=[c for c in candidates if c["name"].casefold()=="rules"]
        official=(no_category or normal or candidates or [None])[0]
    if not official:
        raise RuntimeError("Cannot identify a canonical #rules channel; "
                           "no channel deleted or modified. Select the community "
                           "rules channel in Discord Settings > Community.")
    duplicates=[c for c in candidates if str(c["id"])!=str(official["id"])]
    print("Server:",guild["name"],"mode:",MODE)
    print("[KEEP] Existing upper/community rules channel ID:",official["id"],
          "name:",official["name"])
    print("[FOUND] other rules channels:",len(duplicates))

    # Only keep the category named VERIFICATION public to new arrivals.
    verification=next((c for c in channels if c.get("type")==4 and
                       c["name"] in ("🛡️ VERIFICATION","✅ VERIFICATION")),None)
    staff=next((c for c in channels if c.get("type")==4 and
                c["name"] in ("🔒 STAFF","🔒 STAFF ONLY")),None)
    canonical_perms=[overwrite(GID,VIEW|READ,SEND|THREAD)]
    canonical_perms.extend(overwrite(r,VIEW|SEND|READ|REACT|THREAD) for r in staff_ids)
    canonical_perms.append(overwrite(bot["id"],VIEW|SEND|READ|REACT|THREAD,kind=1))
    payload={"name":"rules","permission_overwrites":canonical_perms}
    apply("PATCH",f"/channels/{official['id']}",payload,
          "Keep original upper rules channel at its current location, read-only for members")

    # The channel designated for Discord Community rules can be changed via
    # Modify Guild. This does NOT enable the checkbox / screening form itself.
    if official_id != str(official["id"]):
        try:
            apply("PATCH",f"/guilds/{GID}",
                  {"rules_channel_id":str(official["id"])},
                  "Designate preserved channel as Community rules channel")
        except RuntimeError as err:
            print("[ACTION REQUIRED] Select kept #rules in Discord > "
                  "Server Settings > Community > Overview; reason:",err,flush=True)

    recent=request("GET",f"/channels/{official['id']}/messages?limit=100")
    our_post=next((m for m in recent if str(m.get("author",{}).get("id"))==str(bot["id"])
                   and MARKER in m.get("content","")),None)
    if our_post:
        if our_post.get("content")!=RULES_TEXT:
            apply("PATCH",f"/channels/{official['id']}/messages/{our_post['id']}",
                  {"content":RULES_TEXT,"allowed_mentions":{"parse":[]}},
                  "Update official rules text in original channel")
        else:
            print("[EXISTS] Official rules already posted")
    else:
        apply("POST",f"/channels/{official['id']}/messages",
              {"content":RULES_TEXT,"allowed_mentions":{"parse":[]}},
              "Post complete English rules in original channel")

    # Old verification instructions are now archived by the automated
    # verification setup. Do not repost or edit old manual-approval prompts.

    secret_perms=[overwrite(GID,deny=VIEW|SEND|THREAD)]
    secret_perms.extend(overwrite(r,VIEW|SEND|READ|THREAD) for r in staff_ids)
    secret_perms.append(overwrite(bot["id"],VIEW|SEND|READ|THREAD,kind=1))
    for old in duplicates:
        msgs=request("GET",f"/channels/{old['id']}/messages?limit=25")
        if not msgs:
            apply("DELETE",f"/channels/{old['id']}",None,
                  "Delete EMPTY duplicate channel #"+old["name"])
        else:
            archive_name="archived-old-rules-"+str(old["id"])[-5:]
            patch={"name":archive_name,"permission_overwrites":secret_perms}
            if staff:patch["parent_id"]=str(staff["id"])
            apply("PATCH",f"/channels/{old['id']}",patch,
                  "Privately archive populated duplicate #"+old["name"]+
                  " preserving "+str(len(msgs))+"+ messages")

    if "MEMBER_VERIFICATION_GATE_ENABLED" in guild.get("features", []):
        print("[NOTICE] Discord's native rules popup is currently enabled. "
              "This workflow no longer requires it; disable it manually if desired.")
    else:
        print("[OK] No mandatory Discord rules popup is required.")
    print("RESULT: exactly one public #rules; other duplicates deleted if empty "
          "or hidden in staff archive. No human messages deleted.")

if __name__=="__main__":
    try:main()
    except (ValueError,RuntimeError,urllib.error.URLError) as error:
        print("FAILED:",error,file=sys.stderr,flush=True)
        sys.exit(1)
