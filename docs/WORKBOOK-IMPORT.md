# Owner-provided Egyptian workbook

The supplied **Egypt Kits.xlsx** contains 527 source rows on 231 terminal
haplogroups. Every row says `Paternal country = Egypt`. The file contains no kit
numbers, YFull IDs, STR marker values, individual SNP paths or test products.
Neither FTDNA kit identities nor Big Y status are inferred.

The importer reads XLSX directly as OOXML with the Python standard library.
It imports only name, paternal ancestor, paternal country and terminal Y
haplogroup. It ignores `About me`, surname collections and maternal ancestors.
Contact details in retained text are redacted. The original workbook and generated
data/SQL stay outside Git; no individual genetic data are committed as fixtures.

## Placement and identity

526 source rows have exact-terminal or exact-prefix ancestry in the saved,
dated public FTDNA reference. These paths are reference ancestry, not additional
individually tested SNPs. `J-L222` remains terminal-only because a verified path
was unavailable. The original terminal is retained first; a different YFull
GitHub reference label is shown second with its immutable source and CC BY 4.0
attribution. No FTDNA/YFull individual identities are joined.

77 paternal-origin texts resolve to one governorate using the existing local
gazetteer. Five ambiguous/conflicting origins remain unassigned for review.
Name text alone is not used as a place: extraction requires exact place
components or explicit paternal location cues such as `قرية`, `مركز` and
`محافظة`. Original retained paternal text and place-source URLs remain available.

86 source rows have a normalized-name candidate in the current archive.
These are **possible matches**, not verified identities. Private reviews contain
record keys and candidate archive IDs. The importer never merges by names or
haplogroups and never assigns one of the anonymous 622 results to a named row.

`ydna_uploaded_files` and `ydna_uploaded_profiles` store source records
separately from the existing archive, external identities and country counts.
All records have `identity_state = unlinked`. Therefore **527 imported rows do
not mean 527 additional unique testers**, and the records do not inflate the
national or regional identified-person statistics. These existing statistics
and all old archive fields remain unchanged until identities can be verified.

The **Y-DNA Tree → Tree dataset → Uploaded profiles** view shows all 527 source
records with their names and available paternal details. The FTDNA country tree
also offers expandable uploaded-record lists at exact matching SNP branches.
Names, SNPs and paternal places are searchable; source-row details cite the
worksheet and Excel row. The old kit/STR and mtDNA views are preserved.

## Repeat imports and removal

`sync/import_workbook.py` generates a read-only plan and batches of calls to
the service-only invoker RPC `ydna_import_uploaded_profiles`. Source records
have deterministic SHA-256 keys over the retained original fields. Reimporting
the same rows creates no duplicates and does not overwrite or republish a
suppressed existing record. Identical source claims across files reuse the
existing record; this is claim deduplication, not proof of a shared person.

Example, using files staged outside the repository:

```sh
python -m sync.import_workbook /tmp/Egypt-Kits.xlsx \
  --snapshot /tmp/verified-country-snapshot.json \
  --archive /tmp/current-public-archive.json \
  --outdir /tmp/egypt-workbook-plan
```

Optional `--yfull` and `--yfull-url` supply the licensed immutable GitHub tree
for secondary reference names. Read `plan.json`, confirm project
`lsfmpmfoqdtkgndtaxen`, and execute its generated SQL batches in order through
the authorized server connection. The dry-run RPC flag defaults to true. No
provider website request is performed. Future uploads are explicit file imports;
this file is not claimed to be an automatically refreshing upstream feed.

The migration is additive, enables RLS, exposes only published files/rows to
public readers and grants import execution to the service role only. Suppressing
a source file hides its source records; individual rows can also be unpublished.
New files default to private. Public release of named genetic/source records
requires the owner's explicit approval of the exact sanitized disclosure.
All 527 records from this upload are currently stored privately; none are
publicly visible pending that approval. A CSV review copy is provided privately
to the owner; it is never committed. The source file's publication flag remains
off during private staging. The private candidate reviews remain private even
if the source file is approved for public display.
Existing archive backups remain intact. Rollback of the UI/importer requires no
deletion or alteration of the old archive.
