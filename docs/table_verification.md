# Table verification checklist

Every reference number used by `concretecalc` lives in `src/concretecalc/data/*.json`.
All values were typed from the project task (section 8), which reproduces the CIE308 Ch4 Part B slides.
**None has been checked against a primary source yet** (`verified_against_primary: false` everywhere).
The slides PDF (`docs/CIE308_Ch4_PartB.pdf`) was not in the repository, so not even a slide cross-check was possible.

## How to verify a table

1. Compare every row below with the slide AND with ACI 211.1-91 / PCA *Design and Control of Concrete Mixtures* (age coefficients: ACI 209R-92).
2. Fill in the slide page, the primary reference (document + table number), your initials and the date.
3. If a value differs: do NOT edit the JSON silently. Add it to `OPEN_QUESTIONS.md`, agree the fix, then change the JSON in its own commit.
4. When every row of a table is checked, set `"verified_against_primary": true` in its JSON and update the test
   `test_every_table_loads_and_cites_a_source` (it currently insists on `false`).

Tables `flag_thresholds` and `required_strength_rules` contain project placeholders and slide rules; for them "primary" means the professor's confirmation.

## Summary

| table | kind | title | verified |
|---|---|---|---|
| `age_coefficients` | mapping | Strength-age coefficients f(t) = f28 * t / (a + b t) | [ ] |
| `air_content` | series | Approximate air content | [ ] |
| `bulk_volume_ca` | grid2d | Bulk volume of dry-rodded coarse aggregate per unit volume of concrete (b/b0) | [ ] |
| `durability` | mapping | Maximum w/c and minimum f'c for durability exposure classes | [ ] |
| `f_factor` | series | Modification factor F for standard deviation by number of tests n | [ ] |
| `flag_thresholds` | mapping | Flag thresholds, validity ranges, input limits and slide rules | [ ] |
| `min_cement_flatwork` | series | Minimum cement content for floors / flatwork (ACI 302) | [ ] |
| `min_cement_misc` | mapping | Other minimum cement contents | [ ] |
| `mixing_water` | grid2d | Approximate mixing water, angular aggregate | [ ] |
| `mixing_water_slump_bands` | mapping | Slump band edges of the mixing-water table | [ ] |
| `required_strength_rules` | mapping | Required average strength f'cr rules | [ ] |
| `shape_reduction` | mapping | Mixing-water reduction by coarse-aggregate shape (subtract from angular values) | [ ] |
| `slump_ranges` | mapping | Recommended slump by type of construction | [ ] |
| `standard_sieves` | mapping | Standard sieve sizes used for maximum size / NMAS selection | [ ] |
| `unit_weight` | series | First estimate of fresh concrete unit weight | [ ] |
| `wc_vs_specified_fc` | series | Water-cement ratio vs SPECIFIED compressive strength f'c (stored, not used by default) | [ ] |
| `wc_vs_strength` | series | Water-cement ratio vs required average compressive strength f'cr at 28 days | [ ] |

## `age_coefficients`

*Strength-age coefficients f(t) = f28 * t / (a + b t)* - kind `mapping`  
Source: ACI 209R-92 (coefficients as given in the project task); verify against ACI 209R-92  
Units: a_days: days; b: -  
Notes: Types II, IV, V use Type I coefficients with a flag. Validity roughly 20-70 MPa (flag_thresholds).

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| moist.type_I.a_days | 4 | | | | |
| moist.type_I.b | 0.85 | | | | |
| moist.type_III.a_days | 2.3 | | | | |
| moist.type_III.b | 0.92 | | | | |
| steam.type_I.a_days | 1 | | | | |
| steam.type_I.b | 0.95 | | | | |
| steam.type_III.a_days | 0.7 | | | | |
| steam.type_III.b | 0.98 | | | | |

## `air_content`

*Approximate air content* - kind `series`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: x: mm (NMAS); non_ae: % (entrapped); ae_mild: %; ae_moderate: %; ae_severe: %  
Notes: Percent as plain numbers (2.0 means 2 %). AE columns by exposure.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| x (axis) | 9.5, 12.5, 19, 25, 37.5, 50, 75, 150 | | | | |
| non_ae | 3, 2.5, 2, 1.5, 1, 0.5, 0.3, 0.2 | | | | |
| ae_mild | 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1 | | | | |
| ae_moderate | 6, 5.5, 5, 4.5, 4.5, 4, 3.5, 3 | | | | |
| ae_severe | 7.5, 7, 6, 6, 5.5, 5, 4.5, 4 | | | | |

## `bulk_volume_ca`

*Bulk volume of dry-rodded coarse aggregate per unit volume of concrete (b/b0)* - kind `grid2d`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: rows: mm (NMAS); cols: - (fineness modulus of fine aggregate); b_b0: - (m3 dry-rodded CA per m3 concrete)  
Notes: FM outside 2.40-3.00 is extrapolated with a flag.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| cols (axis) | 2.4, 2.6, 2.8, 3 | | | | |
| b_b0 @ row 9.5 | 0.5, 0.48, 0.46, 0.44 | | | | |
| b_b0 @ row 12.5 | 0.59, 0.57, 0.55, 0.53 | | | | |
| b_b0 @ row 19 | 0.66, 0.64, 0.62, 0.6 | | | | |
| b_b0 @ row 25 | 0.71, 0.69, 0.67, 0.65 | | | | |
| b_b0 @ row 37.5 | 0.75, 0.73, 0.71, 0.69 | | | | |
| b_b0 @ row 50 | 0.78, 0.76, 0.74, 0.72 | | | | |
| b_b0 @ row 75 | 0.82, 0.8, 0.78, 0.76 | | | | |
| b_b0 @ row 150 | 0.87, 0.85, 0.83, 0.81 | | | | |

## `durability`

*Maximum w/c and minimum f'c for durability exposure classes* - kind `mapping`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: max_wc: - (w/c); min_fc_psi: psi; full_hydration: - (w/c)  
Notes: corrosion_protection = corrosion protection of reinforcement with deicers / seawater. min_fc is stored in psi as given; converted to MPa at lookup.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| low_permeability.max_wc | 0.5 | | | | |
| low_permeability.min_fc_psi | 4000 | | | | |
| freeze_thaw_moist.max_wc | 0.45 | | | | |
| freeze_thaw_moist.min_fc_psi | 4500 | | | | |
| corrosion_protection.max_wc | 0.4 | | | | |
| corrosion_protection.min_fc_psi | 5000 | | | | |
| full_hydration.min_wc_lower | 0.22 | | | | |
| full_hydration.min_wc_upper | 0.25 | | | | |

## `f_factor`

*Modification factor F for standard deviation by number of tests n* - kind `series`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: x: - (number of test results n); f: -  
Notes: Linear interpolation between listed n; F = 1.00 for n >= 30; n < 15 -> standard deviation treated as unknown.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| x (axis) | 15, 20, 25, 30 | | | | |
| f | 1.16, 1.08, 1.03, 1 | | | | |

## `flag_thresholds`

*Flag thresholds, validity ranges, input limits and slide rules* - kind `mapping`  
Source: Project task sections 5-7 (placeholders, ASSUMPTIONS A-10) and CIE308 Ch4 Part B slide rules (Dr. M. Tawk); not from a primary standard  
Units: values: unit given by the key suffix (_m3, _pct, _mpa, _mm, _kg_m3, _days, _ml...); no suffix = dimensionless  
Notes: Thresholds (volume_closure, unit_weight, bulk_ratio, model_spread, slump_estimate.band) are PROJECT PLACEHOLDERS (ASSUMPTIONS A-10, OPEN_QUESTIONS Q15). Input limits come from the project task section 5. slide_rule.* and trial_batch.* are CIE308 slide rules (OPEN_QUESTIONS Q13). Approved as D-1.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| volume_closure.warning_m3 | 0.02 | | | | |
| volume_closure.error_m3 | 0.05 | | | | |
| unit_weight.deviation_pct | 5 | | | | |
| bulk_ratio.deviation_pct | 10 | | | | |
| model_spread_mpa | 5 | | | | |
| slump_estimate.band_mm | 25 | | | | |
| trial_batch.slump_tolerance_mm | 20 | | | | |
| trial_batch.air_tolerance_pct | 0.5 | | | | |
| trial_batch.n_cylinders | 3 | | | | |
| strength_model.wc_min | 0.25 | | | | |
| strength_model.wc_max | 0.85 | | | | |
| age_model.valid_min_mpa | 20 | | | | |
| age_model.valid_max_mpa | 70 | | | | |
| aci_table.basis_nmas_min_mm | 19 | | | | |
| aci_table.basis_nmas_max_mm | 25 | | | | |
| slide_rule.slump_mm | 25 | | | | |
| slide_rule.per_water_kg_m3 | 6 | | | | |
| slide_rule.air_entrainer_ml_per_pct_per_100kg | 6.3 | | | | |
| soft.cement_kg_m3.min | 150 | | | | |
| soft.cement_kg_m3.max | 700 | | | | |
| soft.cement_sg.min | 2.9 | | | | |
| soft.cement_sg.max | 3.3 | | | | |
| soft.coarse_sg_ssd.min | 2.3 | | | | |
| soft.coarse_sg_ssd.max | 3 | | | | |
| soft.coarse_drd_kg_m3.min | 1200 | | | | |
| soft.coarse_drd_kg_m3.max | 2000 | | | | |
| soft.coarse_absorption_pct.min | 0 | | | | |
| soft.coarse_absorption_pct.max | 6 | | | | |
| soft.coarse_mc_pct.min | 0 | | | | |
| soft.coarse_mc_pct.max | 15 | | | | |
| soft.fine_sg_ssd.min | 2.3 | | | | |
| soft.fine_sg_ssd.max | 2.9 | | | | |
| soft.fine_absorption_pct.min | 0 | | | | |
| soft.fine_absorption_pct.max | 8 | | | | |
| soft.fine_mc_pct.min | 0 | | | | |
| soft.fine_mc_pct.max | 20 | | | | |
| soft.fine_fm.min | 2 | | | | |
| soft.fine_fm.max | 3.5 | | | | |
| soft.water_kg_m3.min | 100 | | | | |
| soft.water_kg_m3.max | 280 | | | | |
| soft.air_pct.min | 0 | | | | |
| soft.air_pct.max | 10 | | | | |
| soft.age_days.min | 3 | | | | |
| soft.age_days.max | 365 | | | | |
| soft.bb0_adjustment.min | 0.9 | | | | |
| soft.bb0_adjustment.max | 1.1 | | | | |
| hard.absorption_pct.min | 0 | | | | |
| hard.absorption_pct.max | 20 | | | | |
| hard.mc_pct.min | 0 | | | | |
| hard.mc_pct.max | 30 | | | | |
| hard.age_days.min | 1 | | | | |

## `min_cement_flatwork`

*Minimum cement content for floors / flatwork (ACI 302)* - kind `series`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: x: mm (NMAS); min_cement_kg_m3: kg/m3  
Notes: No values above 37.5 mm NMAS (OPEN_QUESTIONS Q19).

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| x (axis) | 9.5, 12.5, 19, 25, 37.5 | | | | |
| min_cement_kg_m3 | 360, 350, 320, 310, 280 | | | | |

## `min_cement_misc`

*Other minimum cement contents* - kind `mapping`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: values: kg/m3  

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| severe_exposure | 334 | | | | |
| underwater | 385 | | | | |

## `mixing_water`

*Approximate mixing water, angular aggregate* - kind `grid2d`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: rows: mm (slump band midpoint); cols: mm (NMAS); non_ae: kg/m3; ae: kg/m3  
Notes: Rows are the midpoints of the slump bands 25-50 mm (37.5), 75-100 mm (87.5), 150-175 mm (162.5); band edges are in mixing_water_slump_bands. Values are for angular aggregate; subtract shape_reduction. No value at 150 mm NMAS for 150-175 mm slump.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| cols (axis) | 9.5, 12.5, 19, 25, 37.5, 50, 75, 150 | | | | |
| non_ae @ row 37.5 | 207, 199, 190, 179, 166, 154, 130, 113 | | | | |
| non_ae @ row 87.5 | 228, 216, 205, 193, 181, 169, 145, 124 | | | | |
| non_ae @ row 162.5 | 243, 228, 216, 202, 190, 178, 160, null | | | | |
| ae @ row 37.5 | 181, 175, 168, 160, 150, 142, 122, 107 | | | | |
| ae @ row 87.5 | 202, 193, 184, 175, 165, 157, 133, 119 | | | | |
| ae @ row 162.5 | 216, 205, 197, 184, 174, 166, 154, null | | | | |

## `mixing_water_slump_bands`

*Slump band edges of the mixing-water table* - kind `mapping`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: values: mm  
Notes: Band labels of the mixing_water rows; used by the band-reading option approved as D-2.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| band_low.min_mm | 25 | | | | |
| band_low.max_mm | 50 | | | | |
| band_mid.min_mm | 75 | | | | |
| band_mid.max_mm | 100 | | | | |
| band_high.min_mm | 150 | | | | |
| band_high.max_mm | 175 | | | | |

## `required_strength_rules`

*Required average strength f'cr rules* - kind `mapping`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: values: MPa unless the key says otherwise  
Notes: f'cr = max(f'c + 1.34 s F, f'c + 2.33 s F - 3.45). No data: +7.0 if f'c < 21; +8.5 if 21 <= f'c <= 35; +10.0 if f'c > 35. n < 15 -> standard deviation treated as unknown. Approved as D-1.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| statistical.coef_134 | 1.34 | | | | |
| statistical.coef_233 | 2.33 | | | | |
| statistical.offset_233_mpa | 3.45 | | | | |
| no_data.margin_low_mpa | 7 | | | | |
| no_data.margin_mid_mpa | 8.5 | | | | |
| no_data.margin_high_mpa | 10 | | | | |
| no_data.low_band_below_mpa | 21 | | | | |
| no_data.mid_band_up_to_mpa | 35 | | | | |
| f_factor.min_n | 15 | | | | |

## `shape_reduction`

*Mixing-water reduction by coarse-aggregate shape (subtract from angular values)* - kind `mapping`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: values: kg/m3  
Notes: Primary source to be confirmed (OPEN_QUESTIONS Q32).

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| angular | 0 | | | | |
| subangular | 12 | | | | |
| gravel_with_crushed | 21 | | | | |
| round_gravel | 27 | | | | |

## `slump_ranges`

*Recommended slump by type of construction* - kind `mapping`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: values: mm  
Notes: Max may be increased by 25 mm for hand consolidation (stored for mass concrete as given on the slide).

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| reinforced_foundation_walls_footings.max_mm | 75 | | | | |
| reinforced_foundation_walls_footings.min_mm | 25 | | | | |
| plain_footings_caissons_substructure_walls.max_mm | 75 | | | | |
| plain_footings_caissons_substructure_walls.min_mm | 25 | | | | |
| beams_reinforced_walls.max_mm | 100 | | | | |
| beams_reinforced_walls.min_mm | 25 | | | | |
| building_columns.max_mm | 100 | | | | |
| building_columns.min_mm | 25 | | | | |
| pavements_slabs.max_mm | 75 | | | | |
| pavements_slabs.min_mm | 25 | | | | |
| mass_concrete.max_mm | 75 | | | | |
| mass_concrete.min_mm | 25 | | | | |
| mass_concrete.hand_consolidation_extra_mm | 25 | | | | |

## `standard_sieves`

*Standard sieve sizes used for maximum size / NMAS selection* - kind `mapping`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: values: mm  

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| 9.5 | 9.5 | | | | |
| 12.5 | 12.5 | | | | |
| 19 | 19 | | | | |
| 25 | 25 | | | | |
| 37.5 | 37.5 | | | | |
| 50 | 50 | | | | |
| 75 | 75 | | | | |
| 150 | 150 | | | | |

## `unit_weight`

*First estimate of fresh concrete unit weight* - kind `series`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: x: mm (NMAS); non_ae: kg/m3; ae: kg/m3  
Notes: Values appear to be converted from lb/yd3; verify against the ACI 211.1 SI table (OPEN_QUESTIONS Q18).

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| x (axis) | 9.5, 12.5, 19, 25, 37.5, 50, 75, 150 | | | | |
| non_ae | 2276, 2305, 2347, 2376, 2412, 2441, 2465, 2507 | | | | |
| ae | 2187, 2228, 2276, 2311, 2347, 2370, 2394, 2441 | | | | |

## `wc_vs_specified_fc`

*Water-cement ratio vs SPECIFIED compressive strength f'c (stored, not used by default)* - kind `series`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: x: MPa (f'c, specified); non_ae: w/c (-); ae: w/c (-)  
Notes: Different basis from wc_vs_strength (specified vs required average); see OPEN_QUESTIONS Q2.

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| x (axis) | 17, 21, 24, 28, 31 | | | | |
| non_ae | 0.67, 0.58, 0.51, 0.44, 0.38 | | | | |
| ae | 0.54, 0.46, 0.4, 0.35, null | | | | |

## `wc_vs_strength`

*Water-cement ratio vs required average compressive strength f'cr at 28 days* - kind `series`  
Source: CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures  
Units: x: MPa (f'cr, required average = mean strength); non_ae: w/c (-); ae: w/c (-)  
Notes: Moist cured, 19-25 mm aggregate. x stored ascending. AE has no value at 48 MPa. Strength labels look like rounded psi conversions (OPEN_QUESTIONS Q17).

| entry | values | slide page | primary ref (doc, table) | checked by | date |
|---|---|---|---|---|---|
| x (axis) | 14, 21, 28, 35, 41, 48 | | | | |
| non_ae | 0.82, 0.68, 0.57, 0.48, 0.41, 0.33 | | | | |
| ae | 0.74, 0.59, 0.48, 0.4, 0.32, null | | | | |
