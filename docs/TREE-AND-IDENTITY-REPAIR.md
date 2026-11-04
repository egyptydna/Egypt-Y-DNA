# YFull-style trees and identity repair

The existing GitHub Pages site and Supabase project `lsfmpmfoqdtkgndtaxen`
continue to serve the archive. No Vercel deployment, subscription or data API is
required. The archived Tracker parser remains available for local historical
files; the running archive fetcher only reads the owner's Observatory snapshot.
The old hourly Vercel rebuild task is paused. The existing Observatory task
retains its six-hour schedule, with its transfer instructions updated to exclude
Vercel. The GitHub Action retains `23 */12 * * *` for licensed source checks.

## Tree presentation

Both Y-DNA and mtDNA use the same compact, connected rows: clickable blue branch
names, individual sample IDs and origin/test information. Search, filters,
collapse, focus, full paths, source links, STR details/comparison and existing
ancient/study features remain available. Source evidence loads on demand.
Existing lazy rendering, raw-tree caches and archive pagination are retained.

For unambiguous reference matches, FTDNA labels are displayed first and different
YFull branch labels beside them, with the reference version. Multiple FTDNA
branches matching one older YFull branch remain distinct; that cannot establish
identical contemporary branches. Original SNP names and paths are preserved.

J-M319 is J2a. Placement rejects a contradictory J1 ancestry, mixed major
haplogroups and paths that stop before the reported terminal. Proven reference
ancestry is used when available; otherwise the actual tester remains at a
terminal-only node. Source text remains available for review. Bare path markers
such as M172/M410 are understood in J paths. An mtDNA record without a full path
is now shown at its actual published terminal, rather than at its broad letter.
Unpublished intermediate branches are never manufactured.

## Applied additive migrations

- `20261104233924_verified_identity_merges`: current 789-row private backup,
  canonical/retired links, a private merge log and service-only exact-ID merge
  function. Original archive fields are retained in both rows.
- `20261104234339_merged_identity_privacy`: explicit private RLS policy, indexes
  and opt-outs covering both canonical and retired IDs. Identifying merge-log
  payloads are purged during opt-out. Historical protected backup erasure remains
  the documented maintainer procedure.

Two verified pairs were consolidated: YF129136 (519 → 91), preserving U3b3d2a,
its maternal path and YSEQ test; MI33015 (36 → 50), retaining the documented
deeper paternal path. There are 787 active profiles and all 789 stored original
rows. Exact active kit/YFull duplicate counts are zero. A full before/after
comparison confirmed that no pre-existing non-metadata field changed.

MI33015 has conflicting recorded governorates. Both original claims remain
stored; one private origin review is pending. The site excludes this identity
from governorate statistics until resolved, while counting it once nationally.
Its old duplicate-identity review was marked resolved. Identity registration and
observations point to the canonical row, so repeated imports reuse that row.

## Verification and source limits

Run `python -m unittest discover -s sync/tests -v`,
`node sync/tests/frontend.test.cjs`, and the disposable PostgreSQL checks from
`.github/workflows/ydna-tests.yml`. `scripts/check_browser.py` reads production
data and substitutes local assets; its synthetic examples exist only inside the
browser, never in Supabase. It also checks mobile overflow and produces preview
images outside the repository.

These changes add no new testers. Licensed YFull GitHub topology checks and the
existing owner-archive transfer continue separately. They do not establish that
every public FTDNA project or the complete current YFull site was checked. The
official GitHub snapshot currently reports v14.06.0; source timestamps remain
visible. Individual profiles require an actually available, authorized feed.
