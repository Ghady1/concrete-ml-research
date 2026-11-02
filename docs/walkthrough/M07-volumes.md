# M07 - volumes, density and packing

All inputs are per m3. Absolute volume uses mass/(SG*1000); aggregate mass and
SG use matching SSD bases. Cement and SCM volumes are reported separately.
Closure is total volume minus 1 m3, and implied air is 100*(1-solids-water).
Density is the mass sum per m3, compared with the ACI reference lookup.

Packing uses OD mass and OD SG=SG_SSD/(1+Abs/100). Its dry-rodded void
fraction is 1-DRD/(SG_OD*1000). The actual bulk ratio is CA_OD/DRD.
All comparisons propagate lookup warnings and structured applicability flags.
Threshold values come from JSON and remain provisional (A-10).

## Three hand exercises

1. Cement 315 kg, SG 3.15: 0.1 m3; water 200 kg: 0.2 m3;
   CA 1060 kg, SG 2.65: 0.4 m3; FA 728 kg, SG 2.6: 0.28 m3;
   air 2%: 0.02 m3. Total=1, closure=0, implied air=2%.
2. The same mix has mass sum 2303 kg/m3. AE reference at NMAS 19 mm is
   2276 kg/m3. Deviation=100*(2303-2276)/2276, about 1.186%, below 5%.
3. With CA absorption 1%, DRD 1600 kg/m3, SG_OD=2.65/1.01;
   void=1-1600/(SG_OD*1000). Actual b/b0=(1060/1.01)/1600;
   reference at 19 mm/FM 2.6 is 0.64. Paste=0.32 m3 and fine fraction by
   volume=0.28/0.68, distinct from the mass fraction 728/1788.

## Verification

Tests include hand values (abs 1e-12), positive/negative closure boundaries,
SCM volumes, off-node density interpolation, density warning and a Hypothesis
volume identity. Totals are compared directly to 1 +/- the closure thresholds
to avoid subtractive cancellation at exact boundary values. No rounding is used.
Unphysical extrapolated packing ratios and void fractions return error flags.

Full suite: **473 passed**, Python 3.12. No changes to reference values or
approved signatures; no new professor questions.
