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
