# M12 - ten-step Mode A design

`mix_design.py` exposes one pure function for each course step, frozen step
results, `design_mix`, and `to_mode_b_inputs`. All quantities are SI. Each step
retains its intermediate values and flags. The orchestrator propagates its
policy through private calculation helpers without changing approved public
step signatures; standalone water/air and unit-weight steps default to clamp,
while strength and packing default to extrapolate.

1. Slump uses the element maximum unless overridden; mass concrete allows the
   stored hand-consolidation increment.
2. Size selection uses the smallest geometric limit and the next smaller sieve;
   explicit NMAS overrides are reported as user-specified. A limit below the
   supported sieves returns an error-level flag, never a valid size claim.
3. Water uses the approved band reading (D-2), subtracts shape reduction and any
   supplied water-reducer fraction; air comes from the matching lookup.
4. Required-mean strength determines w/c. Durability may lower it; the conflicting
   specified-strength table is comparison only. Minimum durability fc warnings
   do not silently raise the user's fc.
5. Cement is water/wc or the highest applicable minimum; final w/c is recomputed.
6. Coarse OD mass is DRD*b/b0*adjustment; SSD mass includes absorption.
7. Fine SSD mass fills the remaining absolute volume. The density-based weight
   method and its signed difference (weight method minus volume method) are shown.
8. Both course and strict field corrections are calculated (A-20/Q25).
9. Field mass proportions are normalised to cement=1.
10. Field masses scale by batch m3 and carry trial-batch guidance.

Nonpositive remaining fine volume raises; nonpositive adjusted added water is
flagged. Field reports retain the shared research disclaimer. Conversion to
Mode B uses selected field weights per m3 on the as-received basis.

## Three hand exercises

1. Form dimension 200 mm -> 40 mm; spacing/cover 40 mm -> 30 mm.
   Governing limit 30: max sieve 25, NMAS 19 mm.
2. fc=25 -> required mean=33.5 MPa. Non-AE interpolated w/c is
   0.57+(33.5-28)*(0.48-0.57)/7=0.4992857142857143. With water
   205 kg/m3 and no minimum, cement=205/wc. CA_OD=1600*0.64=1024 kg/m3;
   CA_SSD=1034.24 at 1% absorption. Subtract their absolute volumes plus air
   from 1 m3 to obtain FA_SSD.
3. Moisture example field weights CA=1978.8, FA=1176.6, water=250.65,
   cement=580 give proportions approximately 1:2.03:3.41:0.43. A 0.1 m3
   batch multiplies each mass by 0.1. The strict convention uses different field
   weights; compare both rather than mixing their bases.

## Verification

Tests cover individual steps, the required NMAS and proportions examples,
strength/durability/minimum-cement governance, water-reducer arithmetic, policy
raise, nonphysical volume rejection and Hypothesis volume closure. Mode A ->
Mode B tests recover design water under both conventions and SSD masses under
strict; the table mean is within 0.5 MPa of required mean when strength governs.
Other models use an explicit 4.5 MPa research discrepancy tolerance. When a
durability limit governs, the table prediction exceeds the required mean.

Full suite: **619 passed**, Python 3.12. A-48 documents numeric-rule placement
and edge behavior. No public signature changes or new professor questions.
