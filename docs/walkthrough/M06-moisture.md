# M06 - aggregate moisture and water corrections

`moisture.py` resolves oven-dry, SSD and as-received aggregate masses. All
moisture percentages use the OD mass as denominator. Signed free water is
OD * (MC - Abs)/100; a negative result is preserved and flagged. SSD inputs
use MC=Abs regardless of the entered MC (a mismatch is flagged).

The course and strict field-weight functions are separate. Course applies the
slide expressions directly to design masses. Strict first divides SSD mass by
1+Abs/100, then applies the moisture correction. Both return the convention and
signed component water contributions. Negative adjusted added water is preserved
in the result for downstream reporting; these functions do not silently clamp.

## Three hand exercises

1. Course example, all masses in lb/yd3: water 320, CA 1940 (MC 2%, Abs 1%),
   FA 1110 (MC 6%, Abs 1.5%). Wet CA=1978.8, wet FA=1176.6,
   added water=320-19.4-49.95=250.65. The same calculation is tested after
   conversion to SI and back, with absolute tolerance 1e-9 lb/yd3.
2. Treating the same 1940/1110 design masses as SSD gives strict wet weights
   1940*1.02/1.01 and 1110*1.06/1.015; added water is
   320-1940/101-1110*4.5/101.5. This differs intentionally from the course result.
3. For OD aggregate 1000 kg, MC 0.5%, Abs 2%, free water=-15 kg. Thus this
   aggregate reduces effective water by 15 kg. SSD mass is 1020 kg; actual
   stockpile mass is 1005 kg. Water plus aggregate mass is conserved.

## Verification

Full suite: **458 passed**, Python 3.12. Hypothesis checks basis invariance,
strict correction round trips and water/aggregate mass conservation at rel 1e-12.
Hard invalid-input cases are also tested. Architecture tests scan the new module.
No new data values, public signature changes, assumptions or professor questions.
