# M09 - strength models, provisional fits and age

`strength/__init__.py` defines frozen MixState, ModelConstants and
StrengthPrediction objects. Every prediction carries the shared disclaimer,
parameter values, source and calibrated flag. `registry.py` maps names to pure
functions and reads presets through the lookup layer. Curves hold water, air,
and cement SG fixed while varying cement to change w/c.

`aci_table.py` inverts the required-average table, not the specified-strength
table. `abrams.py` uses A/B**wc; `bolomey.py` uses K*(1/wc-0.5). They use
separate AE/non-AE fits without a second air correction. `feret.py` uses
K*(Vc/(Vc+Vw+Va))**2 and therefore includes air explicitly.

`calibration/fit.py` is numpy-only and fits the defaults using the approved
least-squares equations. It reports R2 (log space for Abrams), MPa-space R2
and MPa RMSE. These are table fits, not material calibration; calibrated stays
false. Dataset I/O and calibration storage remain M14 work.

`model_constants.json` stores full-precision project fits and clearly labelled
unverified literature alternatives. The new presets envelope is validated by
`load_presets()`. Fresh dictionaries isolate callers from each other. The
7-day Abrams alternative is stored but rejected for 28-day outputs.

`age.py` reads the ACI 209 coefficients and computes t/(a+b*t). The default
is literal. Optional normalisation divides by 28/(a+28*b). Cement II/IV/V use
Type I coefficients with a flag. Predictions outside the stated strength basis,
low w/c, uncalibrated models and extrapolation all carry flags. Models assume
constant materials, placement, curing and test conditions; they are research
predictions, not design values.

## Three hand exercises

1. Non-AE table: w/c=0.57 gives 28 MPa exactly through `aci_table`.
   For any Abrams A,B with B>1, multiplying B**wc by B**0.1 increases
   the denominator, so increasing w/c by 0.1 decreases strength.
2. Feret AE table point at w/c=0.32: W=184, C=575 kg/m3;
   Vc=575/3150, Vw=0.184, Va=0.05 m3. K=230.00330523607096 gives
   44.17086411386907 MPa, versus table 41 MPa. This 3.170864 MPa discrepancy
   is retained. Owner approved abs 3.2 MPa tolerance, replacing the inconsistent
   original 2.5 MPa criterion. The data and fit were not tuned.
3. Moist Type I at 28 days: factor=28/(4+0.85*28)=1.0071942446.
   Steam Type I: 28/(1+0.95*28)=1.0144927536, outside 1% but within 1.5%
   (Q20). Normalisation makes either factor exactly 1 at 28 days.

## Verification

Property tests cover monotonicity for all models and both AE states. Tests refit
the JSON constants, compare predictions to table nodes with explicit model
tolerances, exercise age normalisation and coefficient fallback, reject malformed
presets, and verify exact synthetic fits and reported statistics. A-46 records
degenerate-fit behavior. No primary verification claim is made for any table.

Full suite: **538 passed**, Python 3.12. Deviation: Feret abs 3.2 MPa
pointwise tolerance as explicitly approved by the owner on 2026-11-02.
