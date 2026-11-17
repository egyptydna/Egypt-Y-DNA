"""Generate review-only Y-DNA slides from already-published Egypt archive records."""
import argparse
import base64
import hashlib
import io
import json
import os
import re
import textwrap
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = "egyptydna/Egypt-Y-DNA"
DB = "lsfmpmfoqdtkgndtaxen"
FIELDS = "id,created_at,sync_visibility,owner_active,origin_raw,governorate,y_dna,test_type,full_snp_path,y_link_1,y_link_2"

def api(url, method="GET", body=None, headers=None):
    data = json.dumps(body).encode() if body is not None else None
    hdr = {"Accept": "application/json", "User-Agent": "EgyptYDNA-TikTok-review"}
    if data is not None:
        hdr["Content-Type"] = "application/json"
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        # Never print tokens, URLs with secrets, or response bodies.
        raise RuntimeError(f"Remote service HTTP {exc.code}") from None

def gh(method, path, body=None):
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN missing")
    return api("https://api.github.com" + path, method, body, {
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28"})

def db(params):
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError("Existing SUPABASE_SERVICE_ROLE_KEY missing")
    url = (f"https://{DB}.supabase.co/rest/v1/Modern_published_samples?"
           + urllib.parse.urlencode(params, safe="*,.()"))
    return api(url, headers={"apikey": key, "Authorization": "Bearer " + key})

def sources(r):
    accepted = {"www.familytreedna.com", "familytreedna.com",
                "discover.familytreedna.com", "www.yfull.com", "yfull.com"}
    out = []
    for key in ("y_link_1", "y_link_2"):
        val = str(r.get(key) or "").strip()
        p = urllib.parse.urlparse(val)
        if p.scheme == "https" and p.hostname in accepted and val not in out:
            out.append(val)
    return out

def eligible(r):
    origin = str(r.get("origin_raw") or "")
    return (r.get("sync_visibility") == "public"
            and r.get("owner_active") is True
            and bool(re.search(r"(?<!\w)(?:Egypt|مصر)(?!\w)", origin, re.I))
            and bool(re.fullmatch(r"[A-T][A-Za-z0-9]*-[A-Za-z0-9._*-]+",
                                  str(r.get("y_dna") or "")))
            and bool(sources(r)))

def lineage(r):
    terminal = r["y_dna"]
    path = str(r.get("full_snp_path") or "")
    nodes = [x.strip() for x in re.split(r"\s*(?:>|→|,)\s*", path) if x.strip()]
    return nodes[-6:] if nodes and nodes[-1].upper() == terminal.upper() else [terminal]

def fingerprint(r):
    return hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]

def label(r):
    return "EG-" + str(int(r["id"]))

def caption(r):
    place = str(r.get("governorate") or "").strip()
    if place in ("", "—", "-"):
        place = "Egypt (region not specified)"
    return (
        f"Egyptian Y-DNA | Haplogroup {r['y_dna']}\n\n"
        "An archive entry with stated Egyptian paternal ancestry is available for review.\n"
        f"Reported region: {place}\n"
        f"Test: {r.get('test_type') or 'Not specified'}\n"
        f"Recorded lineage: {' → '.join(lineage(r))}\n\n"
        "The haplogroup does not by itself establish a migration route or ethnicity.\n"
        "Sources:\n" + "\n".join(sources(r)) +
        "\n\n#EgyptYDNA #YDNA #Egypt #GeneticGenealogy"
    )

def render(r, folder):
    from PIL import Image, ImageDraw, ImageFont
    folder.mkdir(parents=True, exist_ok=True)
    bg, gold, light, muted = "#101a2b", "#e6bd65", "#f7f3ea", "#aeb8c4"
    def font(size, bold=False):
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/" + name, size)
    place = r.get("governorate")
    if place in ("", "-", "—", None):
        place = "Region not specified"
    slides = [
        ("NEW EGYPTIAN Y-DNA", r["y_dna"], "Paternal origin: Egypt\n" + str(place), "PUBLIC ARCHIVE RECORD"),
        ("Y-DNA LINEAGE", " → ".join(lineage(r)), "Only source-recorded SNP steps shown.\nNo invented migration routes.", "PHYLOGENETIC CONTEXT"),
        ("SOURCE & DETAILS", label(r), "Test: " + str(r.get("test_type") or "Not specified")
         + "\nProviders: " + ", ".join(sorted(set(urllib.parse.urlparse(u).hostname for u in sources(r)))),
         "VERIFY PRIMARY SOURCES BEFORE APPROVAL"),
    ]
    def multiline(draw, text, y, textfont, color, wrap=24):
        for para in text.split("\n"):
            for part in textwrap.wrap(para, width=wrap, break_long_words=True) or [""]:
                draw.text((105, y), part, font=textfont, fill=color)
                y += round(textfont.size * 1.4)
            y += 25
        return y
    for number, (title, middle, detail, foot) in enumerate(slides, 1):
        img = Image.new("RGB", (1080, 1920), bg)
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((56, 54, 1024, 1866), radius=45, outline="#927840", width=3)
        d.text((105, 130), "EGYPT Y-DNA PROJECT", font=font(37, True), fill=gold)
        d.line([(105, 279), (975, 279)], fill=gold, width=7)
        multiline(d, title, 355, font(42, True), light, 28)
        y = multiline(d, middle, 555, font(75 if number != 2 else 47, True), gold, 20)
        multiline(d, detail, max(880, y + 80), font(37), light, 31)
        d.line([(105, 1610), (975, 1610)], fill="#887547", width=3)
        multiline(d, foot, 1680, font(23, True), muted, 48)
        d.text((105, 1810), f"SLIDE {number} OF 3  |  REVIEW PREVIEW", font=font(23), fill=gold)
        img.save(folder / f"slide-{number}.png", optimize=True)

def getall():
    return db({"select": FIELDS, "sync_visibility": "eq.public",
               "owner_active": "is.true", "order": "created_at.desc", "limit": "1000"})

def issues():
    result = set()
    for page in range(1, 31):
        items = gh("GET", f"/repos/{REPO}/issues?state=all&per_page=100&page={page}")
        for item in items:
            match = re.match(r"\[TikTok Review\] (EG-\d+)\b", item.get("title", ""))
            if match:
                result.add(match.group(1))
        if len(items) < 100:
            return result
    raise RuntimeError("Issue pagination limit reached; deduplication cannot be guaranteed")

def scan():
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    old = issues()
    created = 0
    run_url = f"https://github.com/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID','')}"
    for r in sorted(getall(), key=lambda x: x.get("created_at") or ""):
        if created >= 4:
            break
        if not eligible(r) or label(r) in old:
            continue
        when = datetime.fromisoformat(str(r.get("created_at") or "2000-01-01T00:00:00+00:00").replace("Z","+00:00"))
        if when < cutoff:
            continue
        render(r, Path("tiktok_reviews") / label(r))
        content = (f"<!-- egypt-tiktok:{r['id']}:{fingerprint(r)} -->\n"
                   "**Not published. Review the source, test resolution, origin and SNP path.**\n\n"
                   f"**Archive reference:** {label(r)}\n\n"
                   "### Suggested English caption\n\n" + caption(r) + "\n\n"
                   f"**PNG previews:** [Open workflow artifacts]({run_url}), "
                   "then download egypt-ydna-tiktok-drafts.\n\n"
                   "**Approve:** Actions > Egypt Y-DNA TikTok review > Run workflow > approve, "
                   "enter this issue number. That queues a Buffer notification, NOT an automatic TikTok post. "
                   "Choose a permitted Nasheed in TikTok when notified. Close this issue to reject.")
        gh("POST", f"/repos/{REPO}/issues",
           {"title": f"[TikTok Review] {label(r)} | {r['y_dna']}", "body": content})
        created += 1
    print(f"Created {created} review item(s). Zero TikTok posts published.")

def buffer(query, variables=None):
    token = os.environ.get("BUFFER_API_KEY")
    if not token:
        raise RuntimeError("BUFFER_API_KEY missing")
    result = api("https://api.buffer.com", "POST", {"query": query, "variables": variables or {}},
                 {"Authorization": "Bearer " + token})
    if result.get("errors"):
        raise RuntimeError("Buffer GraphQL error")
    return result.get("data") or {}

def find_channel():
    account = buffer("query { account { organizations { id } } }")
    found = []
    for org in account.get("account", {}).get("organizations", []):
        query = "query { channels(input: { organizationId: " + json.dumps(org["id"]) + " }) { id name service } }"
        found += [x for x in buffer(query).get("channels", [])
                  if str(x.get("service","")).lower() == "tiktok"]
    if len(found) != 1:
        raise RuntimeError(f"Expected exactly one TikTok channel; found {len(found)}")
    return found[0]["id"]

def approve(issue_number):
    if os.getenv("GITHUB_ACTOR") != REPO.split("/")[0]:
        raise RuntimeError("Only repository owner may approve")
    issue = gh("GET", f"/repos/{REPO}/issues/{issue_number}")
    match = re.search(r"<!-- egypt-tiktok:(\d+):([a-f0-9]{20}) -->", issue.get("body") or "")
    if (issue.get("state") != "open" or not issue.get("title","").startswith("[TikTok Review] EG-")
        or not match or issue.get("user",{}).get("login") != "github-actions[bot]"):
        raise RuntimeError("Unverified/open review issue required")
    comments = gh("GET", f"/repos/{REPO}/issues/{issue_number}/comments?per_page=100")
    if any("Buffer notification post ID:" in c.get("body","") for c in comments):
        print("Already sent to Buffer")
        return
    found = db({"select": FIELDS, "id": f"eq.{int(match.group(1))}", "limit": "1"})
    if len(found) != 1 or not eligible(found[0]) or fingerprint(found[0]) != match.group(2):
        raise RuntimeError("Source changed or was withdrawn; approval blocked")
    record = found[0]
    channel = find_channel()
    folder = Path("tiktok_reviews") / label(record)
    render(record, folder)
    urls = []
    for n in (1,2,3):
        pathname = f"tiktok/approved/{label(record)}/slide-{n}.png"
        gh("PUT", f"/repos/{REPO}/contents/{pathname}", {
            "message": f"Approved Egypt Y-DNA TikTok preview {label(record)} slide {n}",
            "branch": "main",
            "content": base64.b64encode((folder/f"slide-{n}.png").read_bytes()).decode("ascii")})
        urls.append(f"https://raw.githubusercontent.com/{REPO}/main/{pathname}")
    mutation = """mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id dueAt } }
        ... on MutationError { message }
      }
    }"""
    result = buffer(mutation, {"input": {
        "channelId": channel, "text": caption(record),
        "schedulingType": "notification", "mode": "addToQueue",
        "assets": [{"image": {"url": u}} for u in urls]
    }}).get("createPost") or {}
    post = result.get("post")
    if not post or not post.get("id"):
        raise RuntimeError("Buffer did not accept the notification: " + str(result.get("message","unknown")))
    gh("POST", f"/repos/{REPO}/issues/{issue_number}/comments",
       {"body": f"Buffer notification post ID: {post['id']}\n\nApproved for Buffer notification. "
                "You must still choose a Nasheed and complete publishing in TikTok."})
    gh("PATCH", f"/repos/{REPO}/issues/{issue_number}", {"state": "closed"})
    print("Queued Buffer notification. Nothing published directly to TikTok.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("scan","approve"))
    parser.add_argument("--issue-number", type=int)
    args = parser.parse_args()
    if args.mode == "scan":
        scan()
    elif args.issue_number and args.issue_number > 0:
        approve(args.issue_number)
    else:
        parser.error("approve requires positive --issue-number")

if __name__ == "__main__":
    main()
