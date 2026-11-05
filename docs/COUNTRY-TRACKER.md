# Egyptian FTDNA country-result tracker

This tracker displays **anonymous published country/branch counts**, including
results without kit numbers. It creates no fictitious tester profiles. The initial
verified snapshot has **622 results across 393 terminal branch groups**. The
baseline is not described as 622 newly discovered people.

## Own tracker and Observatory fallback

`.github/workflows/ydna-tracker.yml` runs at minute 11 every hour, on deployment
of its collector, and manually via **Actions → FTDNA country result tracker → Run
workflow**. GitHub schedules may be delayed. It works without website visitors
and without Vercel. It uses the existing `SUPABASE_SERVICE_ROLE_KEY` Actions
secret and the fixed project `lsfmpmfoqdtkgndtaxen`; no additional secret is needed.

Primary input:

- https://github.com/ftdnastat/ftdnastat.github.io/blob/master/data/egypt.y.json
- `data/compare-tree.y.json`, `version.json`, and `LICENSE` in the same repository.
- Only country totals and terminal branch/count pairs are projected. No names,
  IDs, STRs or individual genetic profiles are collected through this channel.

The source repository publishes these non-identifying aggregate facts. This
specific use follows the owner's request to display published anonymous country
counts. Its MIT software/documentation license is **not** asserted as a license
for individual genetic data, or as authorization to crawl FTDNA/YFull websites.
Existing direct-provider access restrictions are unchanged. Attribution:
**FTDNA public country counts; processing by ftdnastat / Arsen Abdusalamov**.

The collector checks the public GitHub commit, reads immutable source files,
caches them, retries temporary failures, validates totals and records the file's
publication date separately from the poll time. An hourly check cannot detect a
result before the upstream feed publishes it. No real-time coverage of all
FTDNA projects or the live YFull website is claimed.

The owner's Observatory is the second source:
https://egypt-ydna-observatory.kimoeln.chatgpt.site/archive?new=1.
The already configured six-hour owned-archive automation copies its saved
snapshot to the same Supabase project. The hourly tracker reads this mirror;
short-lived Sites credentials are never embedded in GitHub Actions. The
Observatory's own upstream refresh can fail independently. Its saved data are
retained. This is a fallback snapshot, not a guarantee of an independent upstream
provider.

The newest verified complete snapshot is selected. If the primary is healthy
and both feeds have exactly the same terminal count map, the primary is shown.
If a newer backup has different verified counts, it is selected instead. A large
unexpected drop is held for review. Outages never delete the previous snapshot.
Backup ancestry can enrich an exact source label; its date and evidence URL
are preserved. A path from a dated reference is not claimed to be a live tree
version. Missing intermediate SNPs are never invented.

## Website

**Y-DNA Tree → Tree dataset → FTDNA results** shows every counted result as a
gold dot at its published terminal branch. Exact-terminal public archive profiles
appear in an expandable list under that branch, with public kit/name, original
paternal origin, governorate and existing full STR/source detail windows. Profiles
without a kit number remain eligible when their terminal is published. Alias
blocks, shared names and shared haplogroups are never used to identify an
anonymous counted person. Clicking the count group shows count,
evidence, date, SNP path and existing public profiles with exactly that branch
label. Dots visualize a count; they have no persistent personal identity.
Direct counts are disjoint; subtree counts include descendants.

The separate **Tester profiles** view retains kit/YFull IDs, STRs, study and
ancient samples, filtering and existing detail windows. Known profiles are not
added to or subtracted from the anonymous country total: their overlap is not
established individually. Neither governorates nor Big Y status are inferred
from anonymous counts. The existing regional/profile statistics retain their
original meaning.

The embedded **Tracker history & sources** panel shows data date, check date,
selected feed and country-total/branch changes. A country-total increase can be
reported as additional results. A branch increase alone can reflect refinement
or movement and is not described as a new person. The two snapshots are not
summed. The archived Discover summary of 643 differs from the 622 mapped
country results; no 21 invented results or branch assignments are created.

## Storage, safety and verification

The additive `country_result_tracker` migration adds:

- `ydna_tracker_snapshots`: immutable validated count snapshots and source paths.
- `ydna_tracker_changes`: baseline, country-total and branch-count events.
- `ydna_tracker_status`: latest hourly check and selected snapshot.
- Service-only invoker functions `ydna_tracker_publish` and `ydna_tracker_select`.

RLS permits public reads of published snapshots/history and status only. The
service role writes validated snapshots. The collector never writes the existing
archive, tester identity, STR or regional data tables. Existing private archive
backups remain intact; the migration needs no destructive archive operation.
Rollback of the UI/collector leaves all old profiles and new history intact.

Run `python -m sync.track_country` for a read-only primary-feed dry run. For a
local authorized server with the existing secret, `python -m sync.track_country
--apply` saves snapshots. Reports are written to `reports/country-tracker.json`
and uploaded as private Actions artifacts. The report distinguishes primary
failure, saved fallback and unchanged/published/review statuses.

Tests: `python -m unittest discover -s sync/tests`; `node
sync/tests/frontend.test.cjs`; all SQL migrations and
`sync/tests/database-country-tracker.sql` in the disposable CI database; and
`python scripts/check_browser.py` for desktop/mobile live-data display.

## MIT notice for the upstream repository

MIT License

Copyright (c) 2026 Arsen Abdusalamov

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
