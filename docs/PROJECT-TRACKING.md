# Project tracking on GitHub Pages

The tracker uses the site's existing Supabase project `lsfmpmfoqdtkgndtaxen`.
It does not depend on the Vercel tracker or its unavailable Blob store.

## What runs automatically

`Public Y-DNA synchronization` runs on relevant pushes and hourly at minute 23
UTC. GitHub may delay scheduled jobs. It checks the configured permitted source
feeds, saves their partial reports, and then runs `python -m sync.track_projects
--apply`. The existing server-only Actions database secret is reused. No keys
are added to the page, no plan is changed, and visitors do not start imports.

The separate hourly anonymous country-count tracker is retained. A new selected
snapshot with a positive branch change creates an anonymous lineage search.
Refinement or movement between branches does not establish a new person.

## Project directory and resumable searches

The catalog starts with 9,739 valid entries from the owner's saved directory of
9,740 project names and URLs captured on 20 October 2026. One entry had no usable
project URL and is excluded. The compressed metadata-only manifest
has no sample records or genetic results. It is seeded once per manifest version
in batches of 500 and does not overwrite established evidence. The catalog also
combines project labels and public URLs from approved saved
observations, configured sources and the owner's existing private project
candidate directory. It is a catalog of the currently captured directory,
**not a complete live list of every FTDNA project**. The private candidate table
and source credentials remain private.

An exact public FTDNA kit identity creates a persistent project-search target.
The first documented project is the origin. Other projects are checked against
saved published evidence in bounded batches of 32 targets, verified within the
database API time limit. Checks resume with
unprocessed targets, repeat after 24 hours, and repeat when new project evidence
or catalog entries arrive. Names, shared branches and YFull IDs in a generic kit
field cannot confirm an FTDNA membership. The same typed kit can have several
project memberships while remaining one profile. Each membership retains its
original observation and source URL; existing STRs and curated fields are not
rewritten by this tracker.

Anonymous lineage targets have no sample ID. Matching branch records produce
`lineage_candidate` checks only. They never become exact kit matches and are
not merged into a person. Search targets and individual check queues are
service-only. Public status contains counts, timestamps and source outcomes.

## Honest coverage

The page separately shows catalogued projects, projects with saved evidence,
pending targets, targets checked against saved evidence, kits found in further
projects, anonymous lineage searches and checks awaiting provider permission.
`projectSearch.checkedProjectViews` refers to saved-evidence comparisons;
it does not claim a new live provider result-page visit. A project match's
`last_evidence_at` is the saved evidence date, not a promise of current membership.

Direct FTDNA crawling remains gated by the documented provider-access approval;
the direct YFull website is not crawled. Existing approved archive evidence,
licensed YFull GitHub topology and the non-identifying country feed continue
to work. Enabling a missing provider feed requires actual access/republication
approval, not flipping a flag. See [source findings](QUELLENFREIGABE.md).
Unattempted, restricted, failed and partial sources are never presented as a
complete census. `fullCensus` remains false.

## Saved state and new finds

`ydna_project_tracking_status` stores `last_attempt_at`, `last_saved_at`, run state
and the `projectSearch`, `projectDirectory` and `sourcePartialRuns` summaries.
A successful check advances the saved timestamp even when no new kit is found.
A check within 50 minutes of the last saved check returns `recent_skip`; that
does not indicate a failure. An advisory lock prevents concurrent writers.
On an error, the last saved summary and memberships remain available.

The initial database contents are explicitly a baseline. Subsequent first
discoveries receive a fixed `new_until` timestamp 30 days later. Rechecking or
reimporting an existing profile does not reset the window. The profile tree's
NEW badge and filter use that saved timestamp. They do not label an anonymous
count change as an identified new person. Existing profile visibility and
withdrawal rules also protect membership and activity reads.

Browser checks poll only the small status row once per minute while visible.
They retain the previous summary on failure. A newer saved run offers a reload
for profiles instead of repeatedly fetching all profiles and trees.

## Validation

Python tests cover dry runs, bounded requests, expected recent skips and failure
reporting without payloads. SQL scenarios cover exact kits in multiple projects,
idempotence, anonymous candidate separation, the NEW window, partial coverage,
restricted write access and private profile visibility. Frontend checks cover
escaping, safe source links and marker expiry.

```sh
python -m unittest discover -s sync/tests
node sync/tests/frontend.test.cjs
node sync/tests/project-tracker.test.cjs
```

The additive migration and SQL scenarios also run in the disposable CI database.
