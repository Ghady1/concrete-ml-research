# OPEN_QUESTIONS.md

Part A = questions for the professor (Q1-Q16 seeded from the task, Q17+ found while planning).
Part B = decisions for the owner, needed together with PLAN.md approval.
Nothing here has been "fixed" in data or code; defaults are listed in ASSUMPTIONS.md.

## Part A - questions for the professor

1. **Moisture convention.** The slides apply the correction to design weights as if they were dry; strictly, ACI 211 weights are SSD (factor (1+MC)/(1+Abs)). Which is intended? (default: course/slides convention; strict available as a toggle.)
2. **Two w/c tables** are inconsistent in basis (required average f'cr vs specified f'c). Which feeds prediction? (default: the f'cr table.)
3. **Abrams constants** differ by source (A~96, B~7; A~96.55, B~8.2 at 28 d; A~63.45, B~14 at 7 d). Which is the reference set? Calibrate to the lab's own materials?
4. **Cylinder vs cube:** which specimen does the lab use and which conversion factor is accepted?
5. **Age equation:** literal f28*t/(a+bt) gives ~1.007 at 28 d (Type I moist); normalise? Valid roughly 20-70 MPa only. (See also Q20.)
6. **f'cr for f'c > 35 MPa:** slides' equations vs ACI 318 (0.90 f'c + 2.33 sigma). Which?
7. **3000 psi (20.68 MPa) vs the "< 21 MPa" band edge:** +7.0 or +8.5?
8. **Slide values ~37.1 and ~34.3 vs hand calcs 37.01 and 34.22:** is another rounding/F rule used?
9. **Slump-table band midpoints** (37.5/87.5/162.5) as interpolation nodes: acceptable? (See Q26 for the consequence at 75 mm.)
10. **Specific-gravity basis for absolute volumes:** SSD weight with SSD SG (used here) vs ACI's OD weight with OD SG.
11. **Mode A step 4:** "larger of strength vs durability requirement" taken as the lowest w/c. Confirm.
12. **Weight basis of lab-recorded aggregate weights:** one selector for both aggregates, or per aggregate? MC handling when basis = SSD or oven-dry.
13. **Slide rules:** +25 mm slump per 6 kg/m3 water; 6.3 ml air entrainer per 1 % air per 100 kg cement (product-specific). Source/validity?
14. **Off-node NMAS:** warn or interpolate? (default: interpolate + warn.)
15. **Flag thresholds** (volume closure 2 %/5 %, unit weight 5 %, b/b0 +-10 %, model spread 5 MPa, slump band +-25 mm): placeholders until calibrated.
16. **Future SCMs** (fly ash, GGBFS, glass powder): cement replacement by mass or by volume? SG values?

Added during planning:

17. **w/c vs f'cr table strength axis.** The MPa labels 14/21/28/35/41/48 look like rounded conversions of 2000-7000 psi (13.79, 20.68, 27.58, 34.47, 41.37, 48.26 MPa using 1 psi = 0.00689475729 MPa). The rounded labels are stored as given. Should the exact conversions be used instead? The difference moves w/c by up to ~0.01.
18. **Fresh unit-weight table.** The slide values (e.g. 2276/2187 at 9.5 mm) look like conversions from a lb/yd3 table. My recollection is that ACI 211.1 also has its own SI table with slightly different values, but per ground rule 5 nothing has been changed. Please verify against ACI 211.1-91.
19. **Minimum cement for flatwork** has no values above NMAS 37.5 mm. What applies at 50/75/150 mm? (default: no minimum + flag.)
20. **Age factor at 28 days, steam-cured Type I:** 28/(1.0 + 0.95*28) = 1.0145, so the literal formula is 1.45 % off at 28 d. The task's "within 1 %" acceptance holds for moist I (1.0072), moist III (0.9979) and steam III (0.9950), but not steam I. Normalise by default for steam curing?
21. **Inverse required strength (sigma unknown) has two gaps, not one:** f'cr in [28, 29.5) and in (43.5, 45]. Rule used in both: take the lower candidate and flag. OK?
22. **CA void content** = 1 - DRD/(SG*1000). Which SG? ASTM C29 uses the oven-dry bulk SG. The default takes SG_OD = SG_SSD/(1+Abs/100), because only SG_SSD is an input.
23. **Feret K fitted to the w/c table** needs absolute cement and water contents, but the table gives only w/c. The default assumes the mixing-water table at 19 mm, 75-100 mm slump, angular (205 non-AE / 184 AE kg/m3) with air 2.0 % (non-AE) / 5.0 % (AE moderate). Acceptable as a provisional basis?
24. **The w/c-f'cr table is for 19-25 mm aggregate** (moist cured). Should it still be applied unchanged at other NMAS? (default: yes + info flag.)
25. **Course convention in Mode A.** Step 7 gives FA as an SSD mass (absolute volume with SSD SG), while the slides' step 8 treats it as dry. Water still round-trips exactly, but the FA mass is off by a factor (1+Abs/100). With FA Abs 0.8 % that is ~0.8 %; with FA Abs 6 % (Example 1) it is ~6 %. Is that acceptable for teaching? The strict convention is consistent.
26. **Mode A slump target of 75 mm** (the table maximum for most elements). Midpoint interpolation gives non-AE 19 mm water = 201.25 kg/m3. Reading the "75-100 mm" band gives 205 kg/m3. Instructor solutions probably use the band reading. Which?
27. **Cube specimens in Mode B.** Predictions are on a cylinder basis. Is "cube equivalent = cylinder / factor" the intended use of the cube factor? Or should the factor only be used when converting measured lab cubes for calibration?
28. **Examples 1 and 2: unstated inputs.** Ex. 1: air entrainment, element/slump, aggregate shape. Ex. 2: element type for a bridge pier, exposure class, and whether "25 mm" is the maximum size or the NMAS. Ex. 2: freeze-thaw needs min f'c 4500 psi = 31.03 MPa, above the specified 24.1 MPa. Should f'c be raised, or only flagged?
29. **Fitted Abrams constants.** Fitting to the slide table gives non-AE A = 114.9, B = 12.5 and AE A = 96.5, B = 13.4. These are far from the literature A = 96, B = 7, which fits the table poorly. Which should be shown by default before lab calibration? (default: the project fit, labelled uncalibrated.)
30. **Durability minimum f'c above specified f'c:** flag only (default), or raise f'c to the durability minimum?
31. **Sigma given without n** (number of test results). Assume F = 1.00 (n >= 30) and flag, or treat sigma as unknown? (default: F = 1.00 + flag.)
32. **Shape-reduction values** (subangular 12, gravel with crushed 21, round gravel 27 kg/m3). Please confirm their primary source; they are not part of the main ACI 211.1 water table.

## Part B - decisions for the owner

**Resolved 2026-11-01: owner approved all of D-1 to D-6 as recommended** (D-1 add the two JSON files; D-2 option (b): `slump_lookup="band"` for Mode A; D-3 `presets` kind; D-4 store the 7-day preset only; D-5 add `pytest-cov` to the dev extra in M16; D-6 `tests/test_slump.py` and early `calibration/fit.py`).

- **D-1** Numeric rules not covered by the allowed JSON list include the f'cr constants, unknown-sigma margins, slide rules, validity ranges and flag thresholds. Add `required_strength_rules.json` + `flag_thresholds.json`? Or keep them as named module constants with source docstrings?
- **D-2** Mixing-water lookup for the Mode A slump target: pure midpoint interpolation (spec), or an added `slump_lookup="band"` option used by Mode A (recommended)? (Q26)
- **D-3** `model_constants.json` needs one source per preset. Add a `"presets"` JSON kind with its own loader (recommended), or use a mapping with sources in meta.notes?
- **D-4** 7-day Abrams preset: store only (recommended), or convert to 28 d with the age model?
- **D-5** Coverage summary in M16: add `pytest-cov` to the dev extra, or provide a manual test inventory instead?
- **D-6** Extra test file `tests/test_slump.py` (not in the allowed list), and creating the numpy-only `calibration/fit.py` early in M9. OK?

## Notes for the owner (not questions for the professor)

- Your package name `concrete_ml` is also the import name of an unrelated PyPI package ("concrete-ml" by Zama). Installing that package into the same venv would collide. Nothing to do now; just be aware.
- `requirements.txt` is UTF-16 (PowerShell `>` redirection). pip handles it, but many tools and GitHub diffs don't. `pip freeze | Out-File -Encoding utf8 requirements.txt` avoids that. I did not touch the file.
- The slides PDF `docs/CIE308_Ch4_PartB.pdf` is not in the repo, so no table could be cross-checked against it.
