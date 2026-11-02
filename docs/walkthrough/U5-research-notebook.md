# U5 — versioned notebook and reproducibility record

`provenance.py` fingerprints sorted engine source/reference files, returned
parameters and submitted inputs/settings, alongside runtime/package versions and
UTC time. API schema v2 includes this record; legacy snapshots are labelled as
missing fingerprints. Hashes identify a version, not a guarantee of scientific
validity or an embedded copy of the software. Keep the matching checkout.

`snapshot-store.ts` reads legacy session arrays, writes a v2 envelope and supports
explicit opt-in local persistence. Lab uploads are not stored. JSON imports are
size/shape checked before replacement. Malformed notebooks do not overwrite
existing items. Compare supports rename/description/duplicate, reference choice,
signed/percentage differences, undoable removal and JSON/CSV export. Zero
reference denominators produce no percentage. All constants and flags remain
inside snapshots. Three-snapshot limit is retained.

Verification: 674 Python tests pass, including fingerprint stability and changed
input detection; frontend unit test and production build pass. Chrome/Edge
notebook test exercises rename, duplicate, removal/undo, explicit persistence
in a fresh tab, versioned import/export and rejection of an invalid archive.
Full existing browser regression is run for the checkpoint.

Hand exercises:
1. Export two analyses with water changed: input fingerprint changes, parameter
   fingerprint remains identical when the same constants are used.
2. Use a zero closure reference: inspect why percentage difference is unavailable.
3. Duplicate/rename a snapshot: numerical results stay identical; no rerun occurs.
