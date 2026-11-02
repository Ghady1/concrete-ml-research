# U3 — quantitative coverage and figure exports

The presentation layer derives applicable table w/c bounds and element slump
limits from existing engine reference points/lookups. No new material law.
Strength charts mark table coverage; captions distinguish sweep extrapolation
from the selected policy used for the mix lookup. Coverage is not validation.
Volume plots show actual discrepancy and rounded hover values without normalizing.

`chart-export.ts` exports the rendered SVG with a title/method caption, rasterizes
it at 3x resolution for PNG and serializes full-precision plotted CSV values.
Accessible download names contain the visible SVG/PNG/CSV labels. Numerical
tables remain available. No new dependency or core equation change.

Verification: 672 Python tests pass, including reference-bound and chart-total
reconciliation. Production build passes. Chrome/Edge download checks verify SVG
caption, PNG signature and CSV units. Accessibility tests caught a label-content
mismatch on the new export controls; labels were corrected and the six targeted
Chrome/Edge checks pass. The other 12 workflow checks passed in the full run.

Hand exercises:
1. Confirm non-AE table coverage .33–.82 and AE .32–.74 w/c from stored points.
2. Sum the exported component volumes and compare with the unnormalized total.
3. Compare a rounded displayed mean with its CSV number; only display is rounded.
