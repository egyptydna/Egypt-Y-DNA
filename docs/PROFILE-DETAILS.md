# Profile details, new results and tree presentation

The Y-DNA and mtDNA views use a compact classic scientific tree layout: gold
header, green branch labels, fine elbow connectors, small sample rows and
source-backed age annotations where available. This is the Egyptian archive's
own data and interface; it is not the YFull service or a live copy of its trees.
Unpublished ages, mutations, paths and sample identities are never generated
to fill visual gaps.

Click a profile in a tree, the archive, a chart's sample list or **New results**
to open the same details window. Chart cards also work by keyboard. Maternal
charts open the mtDNA path even when the last tree visited was Y-DNA.

The default path starts at a documented major branch, such as E-V13, and ends
at the published terminal. mtDNA similarly starts at a documented haplogroup.
A start branch is used only if it occurs in the saved source path. A missing
path remains terminal-only; a contradictory terminal is not silently repaired.
Full source paths and reference ancestry remain available inside the profile
window, separately labelled. They no longer expand in archive/chart cards.

## STRs

The existing importer retains original STR marker labels, order, zero values,
microvariants and multi-copy alleles in observations and `ydna_sync_str_values`.
The details window shows those saved values with their project/source URL and
date. Identical repeated claims are reduced in the display; conflicting values
and earlier claims remain distinct. The STR CSV download includes provenance
and protects spreadsheet cells from formula execution. No STR values are
inferred for a SNP-only or YFull record without published STR evidence.

## New results

**New results** lists public FTDNA/YFull profiles during their fixed 30-day
tracking window, with provider and text filters and direct profile actions.
Exact typed IDs determine the provider filter; a YFull ID is not an FTDNA kit.
The original archive is the initial baseline and is not relabelled as new.
Anonymous count changes are listed separately. The existing source approval
restrictions and hourly workflow remain in effect; see
[Project tracking](PROJECT-TRACKING.md).

## Anonymous count groups and identified profiles

Verified public profiles are expanded under their exact published terminal
branch, beside the anonymous count group. A shared branch does not establish
which anonymous result belongs to a named person. No name, STR profile or SNP
sequence is copied onto an anonymous dot, and no arbitrary dot is subtracted.
Profile membership/identity merges still require the existing exact-kit or
explicit cross-provider identity evidence. Country totals and archive-profile
totals retain their separate meanings.

## Verification

`node sync/tests/profile-tools.test.cjs` checks compact paths, missing ancestry,
provider/30-day filters and lossless STR evidence. The frontend regression suite
checks wiring and retained archive behavior. The synthetic browser checks cover
both chart-to-profile flows, both tree styles, keyboard access, STR downloads,
provider filters, anonymous separation and mobile layout. They never download
production individual genetic records.

## Combined tree and archive controls

The default tree overlays every enabled public archive cohort on the saved
FTDNA count topology. Missing YFull/study/ancient terminals are included using
only their validated source or licensed reference path. An exact unique
published ancestor may connect a new branch. Anonymous counts remain unchanged;
profile totals are displayed separately and can overlap them. Ancient records
at intermediate nodes remain visible in compact view. Related ancient references
retain their own category and remain excluded from Egyptian percentages.

Main-group buttons include A, B, E, J1/J2, Q1/Q2 and R1a/R1b/R2 when evidence
supports those assignments. Unresolved J, Q and R records stay in their broad
group. Selecting a group retains the other available filter buttons. SNP search
accepts a full branch or mutation name across the combined saved tree. Archive
and tree profile sorting support alphabetical names, main groups/SNPs and newest
records; sorting never changes tree parentage.

The STR search field has been removed. **Copy STRs** copies marker labels and
alleles from the largest current source panel, in source order, retaining zero,
decimal and multicopy alleles. It does not interleave conflicting project panels
or copy earlier observations as current. The table and CSV retain all evidence.

Both ancient archive tables now open the profile window, including a maternal
path action. Saved dates, site, country, cultural context, description and study
reference appear there. Missing study metadata stays explicitly unavailable;
this presentation change does not invent dates or impute ancient genetic calls.
The existing hourly importer uses bounded batches (32 saved-evidence targets by
default); direct project sources still require their documented permission.

## Owner-confirmed Alexandria correction

On 5 November 2026 the owner explicitly confirmed that the unique ID-less
Al-Iskandariya E entry and its identified YFull entry represent one person.
The specific pair was checked for the same published terminal and governorate,
compatible maternal data and absence of an external identity or synchronized
observations on the older row. The identified profile remains canonical. The
older row is retained as merged, and both complete originals remain in the
private identity-merge audit, along with the source links and correction basis.
The guarded correction was checked in a disposable database for preservation
of originals, idempotency and refusal of changed evidence before application.
No further exact public kit/YFull identity duplicate groups remained in the
aggregate check. Unidentified records still require individual evidence.
This owner confirmation applies only to that pair. It does not introduce
name-, governorate- or haplogroup-based automatic identity merging.
