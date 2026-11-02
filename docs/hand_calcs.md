# Independent course-example calculations (M13)

These formulas were written before running the engine on either example. They
use only task data and ordinary arithmetic, not concretecalc functions. Displayed
answers are rounded here only; tests use abs 0.01 kg/m3, 0.001 w/c, 0.01 MPa.
They are awaiting instructor review, not authoritative design solutions.

## Example 1: 3000 psi foundation

Assumptions: reinforced foundation walls/footings (slump max 75 mm), angular
aggregate, sigma unknown, no durability class specified, no cement minimum.
Compute non-AE and AE moderate. Use nominal 37.5 mm NMAS for the main course
reading; 1.5 inches is actually 38.1 mm, evaluated as a separate off-node variant.
The main values are based on a band reading at 75 mm (approved D-2).

1. Slump range 25-75, target 75 mm.
2. User NMAS 37.5 mm. No geometry limit was supplied.
3. Water=181 non-AE or 165 AE kg/m3; air=1% or 4.5%.
4. fc=3000*0.00689475729=20.68427187 MPa. Since fc<21, fcr=27.68427187.
   Non-AE wc=0.68+(27.68427187-21)*(0.57-0.68)/7.
   AE wc=0.59+(27.68427187-21)*(0.48-0.59)/7.
   Compare the alternative rounded-fc reading: fc=21 -> fcr=29.5;
   wc_non=0.57+(29.5-28)*(0.48-0.57)/7;
   wc_ae=0.48+(29.5-28)*(0.40-0.48)/7. No band is silently changed.
5. C=W/wc, SGc=3.15. No minimum overrides.
6. DRD=105*16.01846337=1681.93865385; b/b0=0.73;
   CA_OD=DRD*0.73; CA_SSD=CA_OD*1.008.
7. V_FA=1-C/3150-W/1000-air/100-CA_SSD/2690;
   FA_SSD=V_FA*2650. Weight-method FA=U-W-C-CA_SSD,
   U=2412 non-AE or 2347 AE.
8. Course: wet_CA=CA_OD*1.02; wet_FA=FA_SSD*1.08;
   water_added=W-CA_OD*0.012-FA_SSD*0.02.
   Strict: wet_CA=CA_SSD*1.02/1.008; wet_FA=FA_SSD*1.08/1.06;
   water_added=W-CA_SSD*1.2/100.8-FA_SSD*2/106.
9. Field C:FA:CA:W divides each selected step-8 mass by C.
10. For a 1 m3 trial, field masses are unchanged. Check slump +/-20 mm,
    air +/-0.5%, fresh unit weight; make 3 cylinders for the 28-day test.

At literal 38.1 mm, interpolation fraction=(38.1-37.5)/(50-37.5)=0.048:
water non=181+0.048*(169-181); AE=165+0.048*(157-165);
air non=1+0.048*(0.5-1); AE=4.5+0.048*(4-4.5);
b/b0=0.73+0.048*(0.76-0.73). Repeat steps 5-10 with these values.

## Example 2: 24.1 MPa bridge pier, AE, freeze-thaw

Assumptions: building column element (beams/reinforced walls has the same
25-100 mm range); slump target=100; round gravel; n=31 so F=1. Compute both
moderate and severe exposure and both interpretations of 25 mm (NMAS=25,
or maximum size=25 -> NMAS=19). No underwater/flatwork condition is assumed.

1. Slump range 25-100, target 100 mm.
2. Use either NMAS 25 or 19 as explicitly labelled.
3. At 25: water=175-27=148; air=4.5 moderate or 6 severe.
   At 19: water=184-27=157; air=5 moderate or 6 severe.
4. Statistical candidates=24.1+1.34*2.4=27.316 and
   24.1+2.33*2.4-3.45=26.242 MPa; fcr=27.316.
   Strength wc=0.59+(27.316-21)*(0.48-0.59)/7=0.4907485714285714.
   Freeze-thaw wc=0.45 governs. Minimum durability fc=4500*0.00689475729
   =31.026407805 MPa exceeds 24.1: flag; do not silently raise fc.
5. C=W/0.45. Severe exposure additionally requires 334 kg/m3; use the
   larger mass. At 25/severe, 148/0.45<334, so min cement governs and
   final wc=148/334. Other variants remain durability-governed.
6. At 25: CA_OD=1681*0.69; at 19: CA_OD=1681*0.64.
   CA_SSD=CA_OD*1.004.
7. V_FA=1-C/3150-W/1000-air/100-CA_SSD/2620;
   FA_SSD=V_FA*2570. Weight-method FA=U-W-C-CA_SSD,
   U=2311 at 25, 2276 at 19 mm.
8. Course: wet_CA=CA_OD*1.015; wet_FA=FA_SSD*1.04;
   water_added=W-CA_OD*0.011-FA_SSD*0.032.
   Strict: wet_CA=CA_SSD*1.015/1.004; wet_FA=FA_SSD*1.04/1.008;
   water_added=W-CA_SSD*1.1/100.4-FA_SSD*3.2/100.8.
9. Divide field FA/CA/water by C for cement=1 proportions.
10. A 1 m3 batch uses these field masses; same trial guidance as Example 1.

## Independent arithmetic results

The following result table is evaluated from the expressions above using only
Python's standard arithmetic (no imports from the engine).

| Case | C | W design | CA OD | FA SSD | Added W course | Added W strict |
|---|---:|---:|---:|---:|---:|---:|
| ex1-False-37.5 | 314.803719 | 181.000000 | 1227.815217 | 659.780922 | 153.070599 | 153.817521 |
| ex1-False-38.1 | 313.801912 | 180.424000 | 1230.237209 | 660.381046 | 152.453533 | 153.201134 |
| ex1-True-37.5 | 340.233234 | 165.000000 | 1227.815217 | 588.037837 | 138.505461 | 139.171164 |
| ex1-True-38.1 | 339.441419 | 164.616000 | 1230.237209 | 587.952503 | 138.094103 | 138.759710 |
| ex2-moderate-19 | 348.888889 | 157.000000 | 1075.840000 | 693.831033 | 122.963167 | 123.139378 |
| ex2-moderate-25 | 328.888889 | 148.000000 | 1159.890000 | 663.352717 | 114.013923 | 114.182394 |
| ex2-severe-19 | 348.888889 | 157.000000 | 1075.840000 | 668.131033 | 123.785567 | 123.955251 |
| ex2-severe-25 | 334.000000 | 148.000000 | 1159.890000 | 620.632699 | 115.380964 | 115.538585 |
