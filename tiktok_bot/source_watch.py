"""Twice-daily source monitoring for Egypt Y-DNA; does not use the owner's archive.

Public third-party ftdnastat publishes dated copies of FTDNA/YFull tree
country-level statistics. It is not a direct scrape of either provider.
"""
import base64
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = "egyptydna/Egypt-Y-DNA"
STATE_FILE = "tiktok_bot/state/provider_watch.json"
BASE = "https://raw.githubusercontent.com/ftdnastat/ftdnastat.github.io/master/"
EGYPT_PAGE = BASE + "en/c/egypt/index.html"
FTDNA_COUNTS = BASE + "data/egypt.y.json"
FTDNA_VERSION = BASE + "version.json"
ROOT_PAGE = "https://ftdnastat.github.io/en/c/egypt/"
UPSTREAM_FTDNA = "https://discover.familytreedna.com/"
UPSTREAM_YFULL = "https://www.yfull.com/tree/"


def request(url, *, method="GET", payload=None):
    headers = {"Accept": "application/json", "User-Agent": "EgyptYDNA-Public-SourceWatch"}
    if url.startswith("https://api.github.com/"):
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise RuntimeError("GitHub Actions token required")
        headers.update({"Authorization": "Bearer " + token,
                        "X-GitHub-Api-Version": "2022-11-28"})
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url,
        method=method,
        headers=headers,
        data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return response.read().decode("utf-8"), response.headers.get("ETag")
    except urllib.error.HTTPError as error:
        if error.code == 404 and url.startswith("https://api.github.com/"):
            return None, None
        # Do not log response bodies or credentials.
        raise RuntimeError(f"Upstream HTTP {error.code}") from None


def github(path, method="GET", payload=None):
    raw, _ = request("https://api.github.com/repos/" + REPO + path, method=method,
                     payload=payload)
    return json.loads(raw) if raw is not None else None


def text_content(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value)).strip()


def extract_new_yfull(html_page):
    # Scope strictly to the named section; never classify historic tree branches
    # as new testers based solely on their presence.
    section = re.search(
        r"<h3[^>]*>\s*New Y-DNA samples in YFull\s*</h3>\s*<ul[^>]*>(.*?)</ul>",
        html_page, flags=re.I | re.S)
    if not section:
        raise ValueError("YFull recent-samples section missing; refusing empty baseline")
    values = [text_content(t) for t in re.findall(r"<li\b[^>]*>(.*?)</li>", section.group(1), re.S)]
    values = [v for v in values if re.fullmatch(r"[A-T][A-Za-z0-9]*-[A-Za-z0-9*._-]+", v)]
    return sorted(set(values))


def extract_snapshot_dates(html_page):
    # Provider snapshots may be older than the moment we checked.
    yf = re.search(r"new samples as of (\d{4}-\d{2}-\d{2})", html_page, re.I)
    ftdna = re.search(r"new kits, (\d{4}-\d{2}-\d{2})\s*→\s*(\d{4}-\d{2}-\d{2})",
                      html_page, re.I)
    if not yf or not ftdna:
        raise ValueError("Source snapshot dates are unavailable")
    return yf.group(1), ftdna.group(2)


def read_sources():
    page, _ = request(EGYPT_PAGE)
    counts_raw, _ = request(FTDNA_COUNTS)
    version_raw, _ = request(FTDNA_VERSION)
    counts = json.loads(counts_raw)
    version = json.loads(version_raw)
    if counts.get("slug") != "egypt" or counts.get("name") != "Egypt":
        raise ValueError("FTDNA country feed is not Egypt")
    if type(counts.get("n")) is not int or counts["n"] < 0:
        raise ValueError("Invalid FTDNA country result count")
    yf_date, ftdna_date = extract_snapshot_dates(page)
    if version.get("yfull", {}).get("snapshot") != yf_date:
        raise ValueError("YFull dates differ between source page and version index")
    return {
        "ftdna_total": counts["n"],
        "ftdna_snapshot": ftdna_date,
        "yfull_snapshot": yf_date,
        "yfull_version": str(version.get("yfull", {}).get("version", {}).get("y", "")),
        "yfull_new_branches": extract_new_yfull(page),
    }


def load_state():
    encoded = urllib.parse.quote(STATE_FILE, safe="/")
    info = github("/contents/" + encoded)
    if not info:
        return None, None
    raw = base64.b64decode(info["content"]).decode("utf-8")
    return json.loads(raw), info["sha"]


def save_state(state, sha=None):
    path = "/contents/" + urllib.parse.quote(STATE_FILE, safe="/")
    body = {
        "message": "Store dated external FTDNA and YFull source monitor snapshot",
        "branch": "main",
        "content": base64.b64encode((json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
                                    + "\n").encode()).decode("ascii"),
    }
    if sha:
        body["sha"] = sha
    result = github(path, "PUT", body)
    if not result:
        raise RuntimeError("Snapshot save failed")


def issue_titles():
    titles = set()
    for page in range(1, 31):
        rows = github(f"/issues?state=all&per_page=100&page={page}")
        for row in rows:
            titles.add(row.get("title", ""))
        if len(rows) < 100:
            return titles
    raise RuntimeError("GitHub issue history exceeded safe deduplication limit")


def open_alert(titles, title, body):
    if title in titles:
        return False
    github("/issues", "POST", {"title": title, "body": body})
    titles.add(title)
    return True


def run():
    current = read_sources()
    previous, old_sha = load_state()
    titles = issue_titles()
    new = 0
    source_note = (
        "Sources: [ftdnastat Egypt — dated FTDNA and YFull snapshots](" + ROOT_PAGE + "), "
        "[FTDNA Discover](" + UPSTREAM_FTDNA + "), "
        "[YFull YTree](" + UPSTREAM_YFULL + ").\n\n"
        "**Important:** Data are taken from a publicly published third-party summary, "
        "not a live scrape or a licensed individual-sample export from either provider. "
        "Do not infer an individual kit ID, geographic migration, ethnicity, or test "
        "type from branch totals.\n\nNo TikTok publication happens automatically."
    )
    # "New" means YFull's new marker in a dated publicly published tree copy.
    # We do not claim this was posted today or reveal a person's identity.
    prev_markers = set(previous.get("yfull_new_branches", [])) if previous else set()
    for branch in current["yfull_new_branches"]:
        if previous and branch in prev_markers:
            continue
        title = f"[TikTok Source Review] YFull Egypt {branch} (snapshot {current['yfull_snapshot']})"
        body = (f"## Candidate — provider-related source change, not yet a verified individual post\n\n"
                f"**Branch:** {branch}\n"
                f"**YFull tree copy:** {current['yfull_snapshot']} "
                f"(reported version {current['yfull_version']})\n"
                "This branch is listed under *New Y-DNA samples in YFull* for Egypt. "
                "The page does **not** establish an individual YFull sample ID here. "
                "Check the original branch and source before creating slides or captions.\n\n"
                + source_note + "\n\n**Status:** For human source verification; no Buffer submission.")
        new += open_alert(titles, title, body)
    # A FTDNA country-total increase indicates added country results; no kit IDs.
    if previous:
        diff = current["ftdna_total"] - int(previous["ftdna_total"])
        if diff != 0 or current["ftdna_snapshot"] != previous.get("ftdna_snapshot"):
            title = (f"[TikTok Source Review] FTDNA Egypt {current['ftdna_snapshot']} "
                     f"({current['ftdna_total']} country results)")
            body = (
                "## Published FTDNA Egypt source update\n\n"
                f"Previous country count: **{previous['ftdna_total']}** "
                f"(snapshot {previous['ftdna_snapshot']})\n"
                f"Current country count: **{current['ftdna_total']}** "
                f"(snapshot {current['ftdna_snapshot']})\n"
                f"Net count change: **{diff:+d}**.\n\n"
                "A count difference can include tree reclassification or corrections. "
                "This report does **not** establish the identity of a new sample. "
                "Check a public original record before making a sample-specific TikTok post.\n\n"
                + source_note + "\n\n**Status:** For human source verification; no Buffer submission.")
            new += open_alert(titles, title, body)
    # Baseline does not create an invented FTDNA event.
    if (previous is None or
        any(current[k] != previous.get(k)
            for k in ("ftdna_total", "ftdna_snapshot", "yfull_snapshot",
                      "yfull_version", "yfull_new_branches"))):
        save_state(current, old_sha)
    print(json.dumps({
        "ftdna_current_count": current["ftdna_total"],
        "ftdna_source_snapshot": current["ftdna_snapshot"],
        "yfull_source_snapshot": current["yfull_snapshot"],
        "yfull_new_branches_in_source": current["yfull_new_branches"],
        "review_alerts_created": new,
        "uses_archive": False,
        "posts_published": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    run()
