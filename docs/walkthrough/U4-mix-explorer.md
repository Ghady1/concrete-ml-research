# U4 — isolated one-variable Mix Explorer

The optional results workspace explores water, cement or age using existing
Mode B requests. A 350 ms debounce and AbortController cleanup prevent stale
responses from winning. Invalid entries preserve the baseline. Unit conversion
uses shared metadata factors and declared batch/per-volume labels.

All other inputs stay fixed. Volume is not automatically balanced, and changing
age leaves base 28-day means unchanged. Baseline and hypothetical values,
selected-age results and original flags are shown separately. Returned parameter
values/source must match the baseline or exploration stops with an explanation.

“Use hypothetical as new evaluation draft” is explicit. It does not recalculate
or overwrite a saved analysis; the previous evaluation becomes stale. Design
exploration transfers into the separate evaluation workspace.

Verification: 672 Python tests, production build and eight targeted Chrome/Edge
checks pass. The Explorer test changes water to 215, verifies exported baseline
water remains 200, then explicitly adopts 215 while cement remains 315.
No new equation, optimizer, model averaging or dependency.

Hand exercises:
1. At 315 kg/m3 cement, compare w/c=200/315 and 215/315.
2. Add 15 kg/m3 water without changing aggregates: volume rises .015 m3/m3.
3. Change age alone: base means stay fixed; selected-age estimates change.
