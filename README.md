# Concrete Research Studio

Local React/TypeScript research studio, pure Python non-ML engine and Streamlit fallback for the LAU project **AI-Assisted
Prediction of Sustainable Concrete Properties**. The calculator implements the
approved CIE308/ACI course methods. Mode B predicts from batch weights; Mode A
produces a ten-step course mix design and can send it back through Mode B.
Calibration fits Abrams, Bolomey and Feret to your own lab records.

**Estimated mean strength (research prediction; NOT a certified structural design value).**
Reference tables remain unverified against primary standards. The course PDF
is not in this repository. Professor questions, including specimen conversion,
moisture basis and coefficient applicability, remain in [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).

## Run the prepared studio

From this checkout in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m concretecalc_web
```

Open http://127.0.0.1:8000. Keep the terminal open; Ctrl+C stops it. For a port
conflict, add `--port 8001` and use http://127.0.0.1:8001. The server binds only
to loopback. After code updates, stop/restart Python and refresh the browser.

The prepared installation includes compiled frontend assets. Node and internet
are not needed to run it. On this machine the build is already prepared.

## Fresh source checkout setup (PowerShell)

Python 3.12 is tested; the package declares Python 3.10+. Use a maintained patch
release. Node is required only to install/build frontend sources.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[web,calibration,dev,app]"
Push-Location web
npm ci
npm run build
Pop-Location
.\.venv\Scripts\python.exe -m concretecalc_web
```

Activation is optional. The app extra keeps the original Streamlit fallback:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

SI/US changes preserve physical quantities. Actual-batch inputs use kg/lb;
per-volume inputs use kg/m3 or lb/yd3. Intended yield is a declared target,
not automatic volume balancing. Numeric research exports retain canonical SI;
figure/comparison exports label their displayed units. Lab CSV/Excel is always SI.

## Studio research workflow

1. **Examples** explains a baseline, moisture contributions, cement overfill and
   two course designs. Examples are not laboratory evidence.
2. **Evaluate/Design** keeps drafts separate from calculated snapshots. Run
   deliberately; inspect the governing design constraint and both moisture bases.
3. **Show the engineering** exposes inputs, water, volumes, constants and age.
   Diagnostics separate engineering concerns from research limitations.
4. **Mix Explorer** changes water, cement or age hypothetically using the same
   engine. Original snapshots stay frozen until explicit draft adoption.
5. **Compare** stores up to three snapshots; rename/describe/duplicate, select a
   reference, inspect signed differences and export the notebook. Local persistence
   is opt-in. Export JSON before clearing browser data; this is not a backup service.
6. **Calibrate** validates local data, selects equations and optionally performs
   a grouped internal holdout. Save explicitly; replacement preserves revisions.
   Independent external validation is still required for accuracy claims.
7. **Report** exports snapshot JSON/CSV, figure SVG/3x PNG/plotted CSV, and a
   browser print layout. Choose Print / PDF, wait for all sections to render,
   and use the browser's Save as PDF option. Return to tab view afterwards.

See [the offline demonstration guide](docs/studio-demo.md),
[the scientific audit](docs/scientific-audit.md), and
[future constituent boundaries](docs/future-constituents.md).

The original `concrete_ml` package, its engineering tests and owner
`requirements.txt` are preserved. That requirements file is a historical
environment snapshot; the extras above are the calculator setup instructions.
Core concretecalc needs numpy only; pandas/openpyxl belong to calibration,
Streamlit/matplotlib to the app, and pytest/Hypothesis/pytest-cov to development.

## Using the calculator

- **Mode B:** enter contents per m3 or declare actual batch volume and weights.
  Explicitly select stockpile/as-received, oven-dry or SSD aggregate basis.
  Enter matching material SG/moisture properties. Automatic air follows the
  reference table until overridden. The report includes water correction, w/c,
  volumes, density/packing, four 28-day means, age adjustment, optional research
  characteristic estimates, slump with placeholder uncertainty, constants and flags.
- **Mode A:** choose targets and geometry or override NMAS. Review all ten
  steps, the governing constraint, both field-moisture conventions and batch
  weights. The prediction-back button shows discrepancies rather than hiding them.
- **Calibration:** download the lab template, delete its two synthetic rows,
  upload CSV or `.xlsx`, review all row errors and select one material set.
  At least three eligible rows are required, with varying w/c for Abrams. Fit
  only actual 28-day records by default, or explicitly convert other ages.
  Save the fit and choose the material set under Prediction constants on a
  subsequent rerun. Missing model fits fall back to labelled uncalibrated defaults.

Read [the lab log guide](docs/experiment_log_layout.md) for every column and
specimen averaging. Cube data requires a user-supplied conversion factor; none
is built in. SCM/SP columns are reserved and ignored by current non-ML fits.
Stored calibration JSON is local and Git-ignored; back it up deliberately.

All flags are data returned by the engine. Error-level flags can accompany an
unphysical or unsupported research result; inspect them before using the numbers.
Abrams assumes constant materials, placement, curing and test conditions.
Slump bands are placeholders, not confidence intervals. Calibration statistics
are in-sample metrics; fitted coefficients do not certify predictive accuracy.

## Engine examples

```python
from concretecalc.schemas import (
    Binder, CoarseAggregateProperties, FineAggregateProperties, MixInputs,
)
from concretecalc.mode_b import run_mode_b, report_to_dict

inputs = MixInputs(
    cement=Binder("cement", 350, 3.15, "cement"), water_kg=180,
    coarse_kg=1000,
    coarse=CoarseAggregateProperties(2.65, 1600, 1, 1, "angular"),
    fine_kg=750, fine=FineAggregateProperties(2.6, 1, 1, 2.6),
    nmas_mm=19, aggregate_weight_basis="as_received",
    air_entrained=False, exposure="moderate",
)
report = run_mode_b(inputs)
data = report_to_dict(report)
```

```python
from concretecalc.calibration.dataset import load_rows, rows_to_fit_arrays
from concretecalc.calibration.fit import fit_all
from concretecalc.calibration.store import (
    save_calibration, load_calibration, file_sha256,
)

rows, errors = load_rows("lab.csv")
# Review errors, select one material_set_id, and obtain >=3 eligible rows.
results = fit_all(rows_to_fit_arrays(rows, age_policy="only_28d"))
for name, result in results.items():
    save_calibration(rows[0].material_set_id, name, result,
                     "lab.csv", file_sha256("lab.csv"))
constants = {
    name: load_calibration(rows[0].material_set_id, name)
    for name in results
}
calibrated_report = run_mode_b(inputs, constants=constants)
```

## Architecture

```text
app/streamlit_app.py (widgets, presentation, upload/store boundary)
        -> app/adapters.py (pure display-unit conversion/formatting)
        -> concretecalc/mode_b.py and mix_design.py (orchestrators)
             -> moisture, volumes, required_strength, slump, strength models
                  -> tables/lookups.py
                       -> loader.py + interpolate.py + models.py
                            -> data/*.json (packaged reference values)

calibration/dataset.py -> shared physical steps -> read-only fitting arrays
calibration/fit.py     -> numpy least-squares fits (pure)
calibration/store.py   -> local JSON I/O; loaded parameters passed to engine
```

Internal units are SI. Functions return frozen dataclasses; warnings are Flag
objects, not prints or UI calls. Architecture tests prohibit Streamlit and
matplotlib imports anywhere under `src/`, and restrict pandas/openpyxl in
concretecalc to the calibration dataset loader.

## Add a strength model (including a future ML model)

1. Implement a pure typed function `(MixState, ModelConstants) -> StrengthPrediction`
   alongside `strength/`. Return 28-day cylinder-basis mean MPa, constants,
   source, calibrated status, flags and the shared disclaimer.
2. Register it in `strength/registry.py:MODEL_REGISTRY`. Supply matching presets
   in `data/model_constants.json`, or pass its ModelConstants explicitly to
   `run_mode_b`. The default loader requires a matching model/preset entry.
3. Add model-domain, provenance, numerical and report/plot integration tests.
   Curves vary cement at fixed water, air and SG. State any different assumptions.
4. Keep ML training/model-file loading at a boundary. Pass trained numerical
   parameters to a pure prediction function; approve any extra dependency or
   required feature/schema expansion before adding it. The current store is
   intentionally scoped to the three parametric fits.

## Reference data and verification

All course numbers are in `src/concretecalc/data/*.json`, with source, units,
notes and `verified_against_primary`. Domain consumers use `tables/lookups.py`.
JSON null means missing data; interpolation never treats it as zero. The
`presets` kind contains provisional fits and unverified literature alternatives.

To verify a table, compare every cell to the actual course/primary source and
record page, reviewer and date in [table_verification.md](docs/table_verification.md).
Report mismatches in OPEN_QUESTIONS.md before changing values. Set verification
metadata only after that review; update the current tests that intentionally
assert false so they reflect the reviewed state. No table has been marked verified.

[Independent course examples](docs/hand_calcs.md) and
[milestone walkthroughs](docs/walkthrough/) show equations, assumptions and hand
exercises. The approved Feret pointwise tolerance is 3.2 MPa; the original 2.5
criterion conflicted with the specified combined fit. Literal steam Type I age
factor at 28 days differs by 1.449%; normalization is optional and explicit.

## Verification commands

```powershell
$testTemp = Join-Path $env:TEMP ("concretecalc-tests-" + [guid]::NewGuid().ToString("N"))
.\.venv\Scripts\python.exe -m pytest -q --basetemp $testTemp --cov=concretecalc --cov=app --cov-report=term-missing
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

A fresh pytest temporary directory avoids an old Windows temp-directory access
problem on the development machine. Tests include physical properties, table
policies, worked examples, calibration, Excel, architecture and Streamlit
interactions including upload/fit/save. Matplotlib uses the Agg backend so the
app never opens a native Tk window from a worker thread. Final results and
packaged-wheel checks are recorded in `docs/walkthrough/M16-hardening.md`.

Historical M16 verification: **655 tests passed, no skips; 96% statement coverage**
across concretecalc and app. `pip check` passed. An isolated installed-wheel
check loaded all 18 reference files and produced a Mode B JSON report without
importing UI/dataframe dependencies. Optional calibration/UI tests skip when
their corresponding extras are not installed; use all extras for full verification.

Studio 2.0 verification is recorded in `docs/walkthrough/U7-release-audit.md`.
The historical coverage figure above does not describe the new web layer.
