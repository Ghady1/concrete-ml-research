# M08 - required average strength and research inverse

The forward rule is max(fc+1.34*s*F, fc+2.33*s*F-3.45).
With unknown sigma, margins are 7 MPa below fc=21, 8.5 MPa from 21 through
35, and 10 MPa above 35. All constants and boundaries come through lookups
from `required_strength_rules.json`; no standard or table value was replaced.

Sigma with n<15 uses the no-data branch and flags insufficient samples. Sigma
with missing n uses F=1 and warns (A-11). The inverse uses exactly the same
margin. Its no-data discontinuities create two gaps; the lower adjacent estimate
is returned with a warning (A-12). A nonpositive inverse is preserved and flagged,
rather than presented as a valid design strength.

## Three hand exercises

1. fc=31 MPa, unknown sigma: required mean=31+8.5=39.5 MPa.
2. fc=31, sigma=3.6, n=17: F=1.16+(17-15)*(1.08-1.16)/5=1.128;
   sF=4.0608. Candidates: 36.441472 and 37.011664 MPa. The second governs.
   The slide's 37.1 differs by 0.088336 MPa (Q8); it is not forced into the code.
3. Mean=29 MPa without sigma lies in the first inverse gap. Adjacent
   candidates are 22 and 20.5 MPa. Use 20.5 and flag the gap. At mean=44,
   adjacent candidates are 35.5 and 34 MPa; use 34 with the same flag.

## Verification

Hand-value tests use abs 1e-9 MPa; separate slide comparisons explicitly allow
0.1 MPa. Hypothesis checks forward/inverse round trips in all valid bands and
with known sigma. Tests cover exact band edges, both inverse gaps, sample-count
fallbacks and invalid inputs. The initial test literal 37.011064 was a
transcription error, corrected to 37.011664 after independently expanding
31+2.33*4.0608-3.45; no implementation constant was changed.

Full suite: **496 passed**, Python 3.12. No new empirical assumptions, public
signature changes or professor questions.
