# M10 - foundational slump estimate

`estimate_slump_mm` delegates inversion to the domain lookup: for the chosen
NMAS, AE state and aggregate shape, water at each available midpoint forms the
inverse curve. Missing high-slump data at NMAS 150 mm is skipped; the two
remaining rows still support inversion and flagged extrapolation.

The estimate retains the lookup status and warnings. Negative extrapolated
slump is floored at zero with an explicit flag. The placeholder uncertainty
band is +/-25 mm, lower endpoint floored at zero; this is not a confidence
interval. Trial-batch tolerance is separately +/-20 mm. An element input adds
a warning when the central estimate is outside its reference slump range.

Admixture effects are not part of this estimate. Mode B will attach an explicit
warning when admixtures are supplied; the M10 public signature is unchanged.

## Three hand exercises

1. At 19 mm, non-AE, angular shape, water=205 kg/m3 inverts to 87.5 mm.
   The placeholder band is 62.5-112.5 mm; trial tolerance is 20 mm.
2. Round gravel subtracts 27 kg/m3: at the same midpoint, water=178 kg/m3
   still inverts to 87.5 mm. Water and slump must use the same shape setting.
3. Slide rule: +6 kg/m3 water gives +25 mm slump; -6 gives -25 mm.
   This is a separate slide approximation, not the derivative of every table
   segment. No numeric rule is embedded in the implementation.

## Verification

Tests cover all three midpoints for five NMAS values, both AE states and two
shapes, including off-node interpolation and the 150 mm missing cell. They also
exercise low/high extrapolation, the zero floor, element warnings and the signed
slide rule. No new assumptions, source changes or public signature deviations.

Full suite: **602 passed**, Python 3.12.
