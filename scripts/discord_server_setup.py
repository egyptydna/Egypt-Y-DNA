#!/usr/bin/env python3
"""Safe, repeatable Discord server bootstrap. No user tokens, no deletions."""
import json, os, sys, time, urllib.request, urllib.error

TOKEN=os.getenv("DISCORD_BOT_TOKEN","").strip()
GID=os.getenv("DISCORD_GUILD_ID","").strip()
MODE=os.getenv("MODE","preview")
BASE="https://discord.com/api/v10"
VIEW=1<<10
SEND=1<<11
THREAD_SEND=1<<38

ROLES=["Founder","Administrator","Moderator","Researcher","Verified Tester","Contributor","Member"]
# (category, channel name, kind: 0=text/2=voice/15=forum, access)
PLAN=[
("📌 INFORMATION", [("welcome",0,"read"),("rules",0,"read"),("announcements",0,"read"),("how-to-submit",0,"read")]),
("🧬 Y-DNA RESULTS", [("new-results",0,"read"),("submit-results",15,"public"),("haplogroup-discussion",15,"public"),("snp-analysis",0,"public")]),
("🗺️ EGYPTIAN ORIGINS", [("governorates",0,"public"),("ydna-map",0,"read"),("ancient-dna",15,"public")]),
("💬 COMMUNITY", [("general",0,"public"),("arabic-chat",0,"public"),("english-chat",0,"public"),("voice-chat",2,"public")]),
("🔒 STAFF ONLY", [("moderation",0,"staff"),("sample-review",0,"staff")]),
]
POSTS={
"welcome":"🧬 **Welcome to Egypt Y-DNA | أهلاً بكم في مشروع DNA المصري**\nResearch Egyptian paternal lineages, SNP trees and genetic genealogy in English or Arabic. Website: https://egyptydna.github.io/Egypt-Y-DNA/\nPlease read #rules and #how-to-submit.",
"rules":"📜 **Server rules / قوانين السيرفر**\n1. Treat everyone respectfully. No hate, insults or spam.\n2. Cite sources and distinguish confirmed SNPs from STR predictions.\n3. No private DNA files, kit IDs, names or exact locations without permission.\n4. Don't present unverified ancestry or tribal claims as established facts.\n5. Moderators may remove misleading or unsafe posts.\nالاحترام والتوثيق العلمي وحماية الخصوصية أساس المشاركة.",
"how-to-submit":"📥 **Submit a sample for review**\nIn #submit-results, provide: publicly supported haplogroup, test type, source URL, SNP-confirmed vs predicted status, and governorate if publicly documented or consented. Kit IDs only with public sourcing/permission. Never upload raw DNA or personal data.",
"new-results":"🆕 **Verified Egyptian Y-DNA results**\nThis channel is for reviewed and sourced results only. The archive is available at https://egyptydna.github.io/Egypt-Y-DNA/",
"ydna-map":"🗺️ **Egyptian Y-DNA map and archive**\nhttps://egyptydna.github.io/Egypt-Y-DNA/\nMap markers are approximate, not home addresses.",
}
def api(method, path, obj=None):
    data=None if obj is None else json.dumps(obj).encode()
    for attempt in range(6):
        req=urllib.request.Request(BASE+path, data=data, method=method,
             headers={"Authorization":"Bot "+TOKEN,"Content-Type":"application/json","User-Agent":"EgyptYDNASetup/1.0"})
        try:
            with urllib.request.urlopen(req,timeout=25) as r:
                body=r.read()
                time.sleep(0.35)
                return json.loads(body) if body else None
        except urllib.error.HTTPError as e:
            body=e.read().decode(errors="replace")
            if e.code==429 and attempt<5:
                try: delay=min(float(json.loads(body).get("retry_after",2)),30)
                except (TypeError,ValueError): delay=2
                time.sleep(delay+0.5)
                continue
            raise RuntimeError(f"Discord HTTP {e.code} for {method} {path}: {body[:350]}")
    raise RuntimeError("Rate limit retries exhausted")

def make(path, obj, label):
    if MODE=="preview":
        print(" [PREVIEW] create",label)
        return None
    result=api("POST",path,obj)
    print(" [CREATED]",label)
    return result

def ov(identity, allow=0, deny=0, kind=0):
    return {"id":str(identity),"type":kind,"allow":str(allow),"deny":str(deny)}

def access_rules(access, roles, bot_id):
    if access=="public": return None
    if access=="read":
        rules=[ov(GID,deny=SEND)]
        for name in ("Administrator","Moderator"):
            if name in roles: rules.append(ov(roles[name],allow=VIEW|SEND))
        rules.append(ov(bot_id,allow=VIEW|SEND,kind=1))
        return rules
    rules=[ov(GID,deny=VIEW)]
    for name in ("Administrator","Moderator"):
        if name in roles: rules.append(ov(roles[name],allow=VIEW|SEND|THREAD_SEND))
    rules.append(ov(bot_id,allow=VIEW|SEND|THREAD_SEND,kind=1))
    return rules

def main():
    if MODE not in ("preview","apply"): raise ValueError("MODE must be preview or apply")
    if not TOKEN or not GID.isdecimal(): raise ValueError("Configure GitHub secrets DISCORD_BOT_TOKEN and DISCORD_GUILD_ID")
    guild=api("GET","/guilds/"+GID)
    bot=api("GET","/users/@me")
    community="COMMUNITY" in guild.get("features",[])
    print("Server:",guild["name"],"| mode:",MODE,"| bot:",bot["username"])
    print("Existing roles/channels are never deleted, moved or modified.")
    roles={r["name"].casefold():str(r["id"]) for r in api("GET","/guilds/"+GID+"/roles")}
    role_ids={}
    for name in ROLES:
        if name.casefold() in roles:
            role_ids[name]=roles[name.casefold()]
            print(" [EXISTS] role",name)
        else:
            created=make("/guilds/"+GID+"/roles",
                {"name":name,"permissions":"0","mentionable":False},
                "role "+name)
            if created: role_ids[name]=str(created["id"])
    channels=api("GET","/guilds/"+GID+"/channels")
    for category, items in PLAN:
        matches=[c for c in channels if c["name"]==category and c["type"]==4]
        parent_id=str(matches[0]["id"]) if matches else None
        if parent_id: print(" [EXISTS] category",category)
        else:
            obj={"name":category,"type":4}
            if MODE=="apply" and category=="🔒 STAFF ONLY":
                obj["permission_overwrites"]=access_rules("staff",role_ids,bot["id"])
            created=make("/guilds/"+GID+"/channels",obj,"category "+category)
            if created:
                channels.append(created)
                parent_id=str(created["id"])
        for name,kind,access in items:
            if any(c["name"].casefold()==name.casefold() and c["type"]!=4 for c in channels):
                print(" [EXISTS] channel",name,"(unchanged)")
                continue
            if kind==15 and not community:
                print(" [SKIP] forum",name,": enable Discord Community and rerun")
                continue
            obj={"name":name,"type":kind}
            if parent_id: obj["parent_id"]=parent_id
            if MODE=="apply":
                permissions=access_rules(access,role_ids,bot["id"])
                if permissions is not None: obj["permission_overwrites"]=permissions
            created=make("/guilds/"+GID+"/channels",obj,"channel "+name)
            if created:
                channels.append(created)
                if kind==0 and name in POSTS:
                    try:
                        api("POST","/channels/"+str(created["id"])+"/messages",
                            {"content":POSTS[name],"allowed_mentions":{"parse":[]}})
                        print(" [POSTED] introduction:",name)
                    except RuntimeError as exc:
                        print(" [NOTICE] Could not post intro:",exc)
    print("Done. Review staff permissions and assign roles manually.")
    if MODE=="preview": print("Preview made NO changes. Select apply to create items.")
    if not community: print("Enable Discord Community for forum channels and rerun apply.")

if __name__=="__main__":
    try: main()
    except (RuntimeError,ValueError,urllib.error.URLError) as exc:
        print("SETUP ERROR:",exc,file=sys.stderr)
        sys.exit(1)
