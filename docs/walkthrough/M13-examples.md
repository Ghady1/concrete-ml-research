# M13 - independent course examples

`docs/hand_calcs.md` was written first, using only task data and independent
arithmetic before calling the engine on either example. It shows all ten steps,
both moisture conventions, the 3000 psi versus 21 MPa band difference and the
freeze-thaw minimum-strength conflict. Its table includes non-AE/AE, nominal
37.5 versus literal 38.1 mm, moderate/severe exposure and NMAS 25 versus
maximum-size 25 -> NMAS 19 variants. Answers have not been edited to match code.

`tests/test_examples.py` compares the engine with those independent answers at
abs 0.01 kg/m3, 0.001 w/c and 0.01 MPa. The examples remain awaiting instructor
review. Q28 lists their unstated inputs; assumptions are explicit in the hand work.

## Three hand exercises

1. Confirm 3000 psi=20.68427187 MPa, then compare +7.0 with the +8.5 MPa
   margin that would apply if fc were rounded to 21 before calculation.
2. Example 1 non-AE: verify CA_OD=1681.93865385*0.73=1227.8152173105
   kg/m3, then independently calculate the remaining fine-aggregate volume.
3. Example 2 at NMAS 25/severe: water=148; strength/durability would require
   C=148/0.45=328.888889, but 334 kg/m3 minimum governs. Final w/c=148/334.
   Repeat with moderate exposure to see why durability governs that variant.

Full suite: **636 passed**, Python 3.12. No mismatches between the engine and
independent calculations at the stated tolerances. No source values changed.
