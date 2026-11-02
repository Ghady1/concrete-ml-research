# M15 - Streamlit boundary, three page commits

The UI lives in `app/`; no engine module imports Streamlit or matplotlib.
`adapters.py` contains pure widget/unit conversion and report formatting.
`streamlit_app.py` collects values with numeric inputs and labelled choices,
calls the engine, and renders returned data. Rounding is display-only.

## Mode B page

Bordered material cards, a prominent aggregate basis selector and explicit help
explain stockpile/OD/SSD interpretation. The default is as received. Automatic
air tracks NMAS/exposure/AE unless the user enables override. UI session state
preserves an air override and converts existing numeric values when units change.
Actual batch weights use kg/lb; per-volume contents use kg/m3 or lb/yd3. Batch
volume uses m3/yd3. Density uses kg/m3/pcf, lengths mm/in, strength MPa/psi.

The page renders 28-day mean and age/characteristic/cube outputs, water breakdown,
volumes, density comparison, packing, slump and placeholder band, all flags by
severity, parameter source and calibration state, plus the prepared w/c plot.
JSON and CSV exports use explicit SI labels regardless of display units. The
research disclaimer is permanent. There is no strength or moisture equation in
the page code; unit conversion is the adapter's boundary responsibility.

## Three hand exercises

1. Convert 350 kg/m3 cement to lb/yd3, then switch the UI units back: the
   adapter should recover 350 kg/m3 without rounding internally.
2. For an actual 0.1 m3 batch, enter 35 kg cement, 18 kg water, 100 kg CA and
   75 kg FA. The reported normalised cement is 350 kg/m3. In US, enter actual
   lb and yd3, not lb/yd3 for this batch-weight mode.
3. At NMAS 19 mm, AE moderate default air=5%. Enable override and set 6%;
   changing aggregate size must preserve 6% until override is disabled.

Mode B page commit: **651 passed**, full suite in project Python 3.12 `.venv`,
including Streamlit defaults, SI/US value preservation and air-override interaction.

## Mode A page

The design page reuses the material cards and pure Mode A adapter. It adds
strength/durability targets, geometry or an explicit NMAS, water reduction,
cement-minimum conditions and batch volume. The selected sidebar moisture
convention determines the field result, with the alternative shown alongside.
All ten steps are collapsible and include intermediate values and the governing
constraint. The design can be exported as SI JSON or sent directly back through
the Mode B engine. No independent design equation is implemented in the page.

Mode A page commit: **652 passed**, full suite, including navigating to Mode A,
rendering all ten steps, predicting the design back through Mode B and switching
the design page to US units without exceptions.

## Calibration page

Uploads accept SI CSV/Excel. Every validation error is shown, with valid rows
retained. Fitting a valid subset requires an explicit checkbox if there are
errors. Users choose one material set and the age policy; fewer than three
eligible rows disables fitting. Results include constants, row counts, R2 with
space, R2 in MPa and MPa RMSE. Changing source bytes/material/age policy hides
stale fit results. Saving writes the three model payloads through the store.

The prediction-constants sidebar lists stored material sets and loads calibrated
parameters for Mode B and the Mode A prediction-back action; absent models use
labelled uncalibrated defaults. Source hashes and warnings remain visible in
prediction reports. CSV/Excel units stay SI even when the calculator is in US.

Streamlit plotting explicitly uses Matplotlib Agg. The Windows Tk default
caused an intermittent worker-thread timeout during AppTest; Agg avoids native
GUI startup. Integration tests exercise upload -> fit -> save with a temporary
store and selecting a stored model for a prediction, as well as all page smoke
and unit/air interactions. The engine remains free of UI imports.

Calibration page commit / completed M15: **655 passed**, full suite in project
Python 3.12 `.venv`, no skips. Three planned page commits, each pushed separately.
