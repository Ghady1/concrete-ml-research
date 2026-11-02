# M14 - calibration and lab records

`dataset.py` is the only concretecalc module importing pandas. It reads the
stable section-10 SI schema from CSV or `.xlsx`, returns valid frozen rows and
all invalid cells with spreadsheet row/column locations. Optional strength
standard deviation may be blank or absent; reserved SCM/SP fields are accepted
and ignored. Cube rows require an explicit extra conversion-factor column.

`rows_to_fit_arrays` uses the same moisture and volume functions as Mode B.
It excludes non-28-day rows by default; the explicit `convert` policy divides
measured strength by the literal age factor. Cube means are first multiplied
by the user's factor. It rejects mixed material sets. Arrays are read-only.
`fit_all` applies the three parametric fits; the comparison table includes n,
R2 in its stated space, R2 in MPa and RMSE in MPa. These are in-sample metrics.

`store.py` is an I/O boundary: safe filename identifiers, SHA-256 source bytes,
UTC timestamps and atomic JSON replacement. One material-set file contains a
`models` mapping, so saving Bolomey does not erase an existing Abrams fit.
Loaded ModelConstants carry calibrated=True, source hash and material-set id.
This records a calibration, not independent verification of predictive accuracy.

The template contains two clearly synthetic rows, intentionally fewer than the
three needed for fitting. Delete them before recording measurements. The lab
guide documents every column, specimen averaging, consistent conditions, age
conversion and the storage envelope.

## Three hand exercises

1. Generate exact Abrams strengths at w/c .3/.4/.5 using f=100/10**wc.
   ln(f)=ln(100)-ln(10)*wc, so a fit should recover A=100, B=10.
2. A 7-day Type I/moist mean is divided by 7/(4+.85*7) for optional
   conversion to 28-day equivalent. An actual 28-day mean is left unchanged.
3. A cube mean of 40 MPa with user factor 0.8 becomes 32 MPa cylinder
   equivalent. Without a factor, the row is rejected; there is no built-in ratio.

## Decisions and checks

A-49 records schema boundary choices and the one-file/multiple-model envelope.
Tests cover noisy synthetic parameter recovery, all-row error accumulation,
default age filtering/conversion, explicit cube handling, reserved columns,
missing headers, fit row count, material-set isolation, store merge/round trip,
hashes and traversal rejection. Excel is tested with the calibration extra.

Full suite: **646 passed**, Python 3.12, including Excel round trip. No new
dependencies beyond the approved calibration extra, no public signature changes.
