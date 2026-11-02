# Offline local demonstration

Setup/build once using README.md. Then launch with:

```powershell
.\.venv\Scripts\python.exe -m concretecalc_web
```

Open http://127.0.0.1:8000. Node is not used by the prepared runtime. All fonts,
photographs, SVGs and charts are local. External source/license links are optional
and need internet; the methods explanations themselves are bundled.
To change port: append `--port 8001`. Stop with Ctrl+C. Restart after updates.

## A five-minute review path

1. Home → Examples → balanced evaluation. Identify illustrative defaults, mass
   basis, record-only fields and declared yield. Run analysis.
2. Open Show the engineering. Explain moisture→effective water→w/c, volume sum
   and the distinction between computed mass per declared volume and measurement.
3. Strength tab: compare four means, coverage shading and controlled w/c sweep.
   Age tab content explains literal/normalized development, not measured history.
4. Open Mix Explorer and raise water. The baseline export stays frozen. Adopt
   the hypothetical only with its explicit button; the old result becomes stale.
5. Save two calculated snapshots. Compare with a selected reference, inspect
   assumptions, export the notebook. Persistence is explicit and device-local.
6. Design a course example. Inspect the governing constraint, all ten steps,
   strict/course field weights and model discrepancies. Require trial batching.
7. Calibration → synthetic demo. Show in-sample vs grouped holdout and fixed
   mix-ID grouping. Do not call the synthetic exercise experimental validation.
8. Export a figure and Print / PDF. Sources, raw inputs and numerical tables
   support review. Finish with limitations and unresolved professor questions.

## Lab records and saved state

Lab files use the stable SI schema in docs/experiment_log_layout.md. Uploads are
temporary, bounded and process-local; server restart requires re-uploading.
At least three rows are needed for fitting. Optional grouped holdout requires
ten distinct mix IDs; this is a project guard, not proof of statistical adequacy.
Use a common mix ID for dependent observations from one experimental mix/batch.
Repeated tuning against a holdout weakens its independence.

Calibrations live in calibrations/<material_set_id>.json. Explicit replacement
archives previous model records. Back this directory up deliberately. Notebook
JSON includes results/constants/provenance but does not embed source code;
keep the matching checkout or prepared wheel for exact replay.

## Rehearsal without internet

After setup, disconnect internet while retaining loopback. Open a fresh browser
tab and complete the sequence above. Do not click external reference links.
Browser tests also block all non-loopback requests and exercise calculations,
examples, calibration and exports. No accounts or cloud services are involved.

## Preparing a wheel with built assets

After `npm run build`, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip wheel --no-deps . -w artifacts/demo
```

Install that wheel with web/calibration extras on the demonstration environment.
For a completely offline fresh environment, pre-download the Python version-
and platform-matching dependencies as well; a single wheel does not bundle them.
The supplied .venv on this machine already has the runtime dependencies.
