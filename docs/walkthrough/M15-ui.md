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
