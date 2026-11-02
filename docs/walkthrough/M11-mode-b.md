# M11 - Mode B complete research pipeline

`run_mode_b` is the public engine entry point for batch-weight prediction. It
validates, scales every mass to per m3, resolves moisture, and computes effective
water, w/c and w/cm. Air comes from the user or the reference lookup. It then
calls volume, unit-weight, packing, model, age and slump functions and gathers
their flags in a frozen StrengthReport carrying the shared disclaimer.

Inputs are retained unchanged alongside normalised report fields. `report_to_dict`
recursively copies dataclasses to JSON-serialisable dictionaries. The plot contains
both available reference point sets and 61 points per model over w/c 0.25-0.85;
it has no matplotlib dependency. NMAS outside 19-25 mm gets a table-basis flag.

Each model returns its constants and provenance. Optional constants override
individual models. Characteristic estimates are reported when sigma or n is
supplied. Cube equivalents require the user's factor and use cylinder/factor;
no specimen conversion constant is assumed. Age-adjusted values remain separate
from the 28-day means. Model disagreement above the chosen threshold is flagged.

AE dosage uses an optional user rate or the JSON slide rate and is always marked
product-specific. Supplied water reducer/superplasticizer information warns that
the slump estimate ignores its effect. SCM affects w/cm and volume but carries
an unsupported-strength-effect warning. See A-47 for boundary behavior.

## Three hand exercises

1. Enter C=315, W=200, CA_SSD=1060, FA_SSD=728 kg/m3 with SGs 3.15,
   2.65, 2.6 and air=2%. Effective water=200, w/c=200/315, total volume=1,
   density=2303 kg/m3. MC=Abs=1% for each aggregate avoids free water.
2. Double every mass and declare batch volume=2 m3. Per-m3 scale=0.5;
   all prediction values must match exercise 1 exactly. Then enter OD aggregate
   masses 1060/1.01 and 728/1.01 at MC=Abs=1%; the same volumes/w/c result.
3. Add 20 kg/m3 SCM: w/cm=200/335 while w/c remains 200/315. Set cube
   factor=0.8: cube-equivalent 28-day means are cylinder means/0.8. With sigma
   2 MPa and n=30, the characteristic margin is max(2.68,1.21)=2.68 MPa.

## Verification

Integration tests check intermediate hand values, batch and basis invariance,
SCM/cube/age/characteristic outputs, table-default air, product dosage, spread
flags, plot dimensions, strict JSON serialization, and invalid/effectively dry
water inputs. The existing architecture test scans the orchestrator.

Full suite: **609 passed**, Python 3.12. No public signature deviations.
