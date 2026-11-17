"""Research alerts for dated, already-synchronized FTDNA totals and YFull tree releases.
These are NOT individual tester discoveries and cannot be sent to Buffer.
"""
import json
import os
import urllib.parse
from datetime import datetime, timedelta, timezone
from .runner import DB, REPO, api, gh


def read_table(name, params):
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not key:
        raise RuntimeError("Missing existing Supabase secret")
    url = (f"https://{DB}.supabase.co/rest/v1/{name}?"
           + urllib.parse.urlencode(params, safe="*,.()"))
    return api(url, headers={"apikey": key, "Authorization": "Bearer " + key})


def existing():
    titles = set()
    for page in range(1, 31):
        items = gh("GET", f"/repos/{REPO}/issues?state=all&per_page=100&page={page}")
        titles.update(item.get("title") for item in items if item.get("title"))
        if len(items) < 100:
            return titles
    raise RuntimeError("Unable to deduplicate research alerts")


def maybe_issue(titles, title, body):
    if title in titles:
        return False
    gh("POST", f"/repos/{REPO}/issues", {"title": title, "body": body})
    titles.add(title)
    return True


def stamp(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    titles = existing()
    created = 0
    # The project's existing background tracker reads published aggregate snapshots.
    # A higher number is not evidence of a particular new individual.
    snaps = read_table("ydna_tracker_snapshots", {
        "select": "source_id,provider,total_count,observed_at,source_url,published",
        "provider": "eq.ftdna", "published": "is.true",
        "order": "observed_at.desc", "limit": "30"})
    for current, previous in zip(snaps, snaps[1:]):
        if current["source_id"] != previous["source_id"]:
            continue
        if stamp(current["observed_at"]) < cutoff:
            continue
        delta = current["total_count"] - previous["total_count"]
        if delta <= 0:
            continue
        day = str(current["observed_at"])[:10]
        title = f"[DNA Source Alert] FTDNA Egypt aggregate {day} {previous['total_count']} to {current['total_count']}"
        body = (
            "**Research alert, not a TikTok draft. No individual person is identified.**\n\n"
            f"A dated published Egypt country count changed from {previous['total_count']} "
            f"to {current['total_count']} (delta +{delta}).\n"
            f"Observed source date: {current['observed_at']}\n"
            f"Source: {current.get('source_url') or 'Original reference in project tracker'}\n\n"
            "Investigate whether this represents additional results, reclassification, "
            "or corrected counts. Do not publish a story about a new tester without "
            "individual primary-source evidence and publication permission.")
        created += maybe_issue(titles, title, body)
    # The official, licensed YFullTeam/YTree GitHub source provides TREE changes,
    # not individual Egyptian provenance; do not invent country-specific samples.
    releases = read_table("ydna_sync_tree_releases", {
        "select": "version,checked_at,published_at,source_url,changes,tree_sha,published",
        "source_id": "eq.yfull-github", "published": "is.true",
        "order": "checked_at.desc", "limit": "10"})
    for release in releases:
        when = stamp(release["checked_at"])
        if when < cutoff:
            continue
        change = release.get("changes") or {}
        changes = {k: v for k, v in change.items()
                   if k in ("new_nodes", "moved_nodes", "removed_nodes",
                            "changed_snp_blocks", "changed_age_estimates")
                   and isinstance(v, int) and v > 0}
        if not changes:
            continue
        title = f"[DNA Source Alert] YFull YTree {release['version']} {str(release['tree_sha'])[:10]}"
        body = (
            "**Tree update only, NOT a newly identified Egyptian tester.**\n\n"
            f"Version: {release['version']}\n"
            f"Published at: {release.get('published_at')}\n"
            f"Detected changes: {json.dumps(changes)}\n"
            f"Licensed source: {release.get('source_url')}\n\n"
            "Before drafting a country-specific TikTok post, verify an Egyptian "
            "individual in a separately permitted public sample source.")
        created += maybe_issue(titles, title, body)
    print(f"Source research alerts created: {created}. Nothing sent to Buffer.")


if __name__ == "__main__":
    main()
