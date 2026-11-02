# U6 — calibration, internal validation and saved revisions

The web boundary uses unchanged engine fitting equations with explicit model
selection. Fit context retains material ID/source hash, age policy, train/test
mix IDs, sample counts, air condition, cement type and curing. Incompatible
conditions must be separated. Stored condition metadata is enforced when
applying a new fit; legacy files without it remain readable.

Optional grouped holdout sorts mix IDs by SHA-256 of `15:<mix_id>`, reserving
max(2, floor(unique_mix_count/5)) groups. At least 10 unique mixes is a project
guard, not a claim of statistical sufficiency. Repeated ages/observations stay
with their mix. Fit parameters use training rows only; held-out rows never
enter fitting. Repeated tuning on this holdout weakens its evidential value.
This is internal holdout assessment, not external validation or cross-validation.
Background rationale: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.GroupShuffleSplit.html
No scikit-learn dependency is added; the deterministic split is project code.

Diagnostics report n, MAE, RMSE and MPa-space R2, with null R2 for constant
targets, plus default-model RMSE on identical observations. Raw original fit
statistics retain their stated log/MPa space. Age conversion is labelled as
model-based. The parity plot distinguishes fitted/default predictions.

`calibration_archive.py` saves a whole selected bundle atomically using the
existing JSON model format. Explicit replacement creates a revision and
archives earlier model records. A lock makes web reads/saves coherent.
Malformed XLSX and oversized observation counts now fail clearly before fitting.
The ten-step design adds orientation and a visible w/c-constraint comparison;
it remains preliminary course proportioning requiring trial batching.

Verification: 679 Python tests pass. Added tests perturb held-out targets and
verify identical fitted coefficients, ensure repeated mix observations stay
together, check undefined R2/hand MAE/RMSE, archive/409 behavior, condition mismatch
and malformed/oversized files. Chrome/Edge cover selected-model held-out fitting,
diagnostic switching, invalidation and explicit saved revisions. Two Chrome
trace-cleanup errors from overlapping browser output were rerun sequentially.

Hand exercises:
1. For measured [2,2] and predicted [2,3], MAE=.5, RMSE=sqrt(.5), R2 undefined.
2. In 12 unique mixes, identify the 2 held-out IDs and confirm no overlap with
   the 10 fitting IDs. Repeat rows without creating independent groups.
3. Save once, attempt replacement without opt-in (409), then save a revision;
   compare old/new records and preserved source/age/split context.
