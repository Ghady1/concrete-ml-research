# M04 - tables/lookups.py: domain-named table lookups

## What this milestone adds

| File | Purpose |
|---|---|
| `src/concretecalc/tables/lookups.py` | Every table read the engine will ever do, with names in engineering words and units |
| `src/concretecalc/units.py` | Exact unit conversions (moved forward from M5: psi -> MPa needed here) |
| `src/concretecalc/schemas.py` | Only the `Literal` type aliases for now (shape, exposure, element, durability class, slump lookup) |
| `tests/test_tables.py` (M4 section) | 136 tests |
| `tests/test_units.py` | 23 tests (hand values + hypothesis round trips) |

**Rule:** engine modules (moisture, volumes, strength, ...) import from `lookups`, never from
`interpolate` or `loader`. `lookups` is the one module that knows table ids, column names and
key spellings, so renaming a JSON column breaks one file, not ten.

## Functions

| function | returns | table | notes |
|---|---|---|---|
| `wc_for_strength(fcr_mpa, air_entrained, policy="extrapolate")` | w/c | wc_vs_strength | AE 48 MPa null dropped |
| `strength_for_wc(wc, air_entrained, policy="extrapolate")` | f'cr MPa | same, inverted | the mean-strength "model" of M9 |
| `wc_for_specified_fc(fc_mpa, ...)` | w/c | wc_vs_specified_fc | stored, not default (Q2) |
| `mixing_water_kg_m3(slump_mm, nmas_mm, air_entrained, shape, policy="clamp", slump_lookup="interpolate")` | kg/m3 | mixing_water - shape_reduction | `"band"` option = D-2 |
| `slump_for_water_mm(water_kg_m3, nmas_mm, air_entrained, shape, policy="extrapolate")` | mm | mixing_water inverted | used by slump.py (M10) |
| `shape_reduction_kg_m3(shape)` | kg/m3 | shape_reduction | |
| `air_content_pct(nmas_mm, exposure, air_entrained, policy="clamp")` | % | air_content | exposure required only if AE |
| `bulk_volume_ratio(nmas_mm, fm, policy="extrapolate")` | b/b0 | bulk_volume_ca | |
| `fresh_unit_weight_kg_m3(nmas_mm, air_entrained, policy="clamp")` | kg/m3 | unit_weight | |
| `slump_limits_mm(element)` | (min, max) Lookups | slump_ranges | |
| `hand_consolidation_extra_mm()` | mm | slump_ranges | +25 mm |
| `f_factor(n_samples)` | F | f_factor + rules | n<15 UNAVAILABLE; n>=30 -> 1.00, status OK |
| `max_wc_durability(class)`, `min_fc_durability_mpa(class)` | w/c, MPa | durability | "none" -> value None, status OK |
| `full_hydration_wc_limits()` | (0.22, 0.25) | durability | |
| `min_cement_flatwork_kg_m3(nmas_mm)` | kg/m3 | min_cement_flatwork | > 37.5 mm UNAVAILABLE |
| `min_cement_misc_kg_m3(condition)` | kg/m3 | min_cement_misc | severe_exposure / underwater |
| `standard_sieves_mm()`, `is_standard_nmas(nmas_mm)` | | standard_sieves | |
| `threshold(key)`, `required_strength_rule(key)` | float | D-1 files | KeyError on a typo |
| `strength_table_range_mpa()`, `fm_table_range()` | (lo, hi) | read from the table axes | no duplicated limits |

## The two non-trivial lookups

### Mixing water, two readings of the slump axis (D-2)
The table rows are *bands* (25-50, 75-100, 150-175 mm), but interpolation needs numbers. Two
ways are offered:

```
 water (non-AE, 19 mm)
 216 |                                   o=========o      band reading
     |                              _/
 205 |               o=====*=====o /                     o interpolate (midpoints)
     |            _/      /
 190 |  o====*===o      /
     |        \______/
     +--25---37.5--50--75--87.5--100-----150--162.5--175--> slump mm
```
- `"interpolate"` (default; task spec): straight lines between the midpoints 37.5 / 87.5 / 162.5.
  At 75 mm it gives 190 + 0.75 x 15 = **201.25** kg/m3.
- `"band"` (D-2; for Mode A): flat inside each band, straight line across the gaps between
  bands. At 75 mm it gives **205**, which is what reading the slide table gives. Outside 25-175
  mm the end band is used with status CLAMPED. A band is never extrapolated (A-41).
  `"raise"` still raises.

In both cases the NMAS direction is linear (22 mm lies halfway between 19 and 25, so 199).
`_water_at_row` reads one slump row through `interp2d` exactly on that row, so a null cell
behaves the same way in both readings.

### Slump from water (the inverse, for Mode B)
For one NMAS/shape there are three (water, slump) points, one per band midpoint. The function
builds them, drops a band with no data (150 mm NMAS has no 150-175 mm value, so only two points
remain, plus a warning naming the band), then calls `interp1d(water -> slump)`. Because water
increases with slump in every column, this inversion is unique. A hypothesis test checks
`slump_for_water(mixing_water(s)) == s` for random slumps and NMAS values.

## Deviations from PLAN.md
- `units.py` (complete, with `tests/test_units.py`) and the `Literal` aliases of `schemas.py` were
  created now instead of in M5. Reasons: `min_fc_durability_mpa` needs psi -> MPa, and the lookups
  take shape, exposure, element and durability-class arguments. The M5 dataclasses are NOT
  written yet.
- New public helpers not listed in PLAN M4: `hand_consolidation_extra_mm`,
  `full_hydration_wc_limits`, `threshold`, `required_strength_rule`, `strength_table_range_mpa`,
  `fm_table_range`. They exist so later modules never open a JSON file or hard-code a number.
- `mixing_water_kg_m3` gained `slump_lookup` (approved D-2).
- `schemas.py` also exports tuples of the allowed values (`AGGREGATE_SHAPES`, ...), because
  `Literal` is not checked at runtime.

## Exercises
1. By hand: mixing water for 60 mm slump, 19 mm NMAS, non-AE, subangular aggregate, with
   `slump_lookup="band"` and with `"interpolate"`. (Band: 50 -> 190, 75 -> 205; midpoints:
   37.5 -> 190, 87.5 -> 205. Don't forget the 12 kg/m3 reduction.)
2. `f_factor(17)`: show that linear interpolation between n = 15 (1.16) and n = 20 (1.08) gives
   1.128. Why does `f_factor(40)` have status OK and not CLAMPED?
3. With 150 mm NMAS, non-AE, angular aggregate: what slump does `slump_for_water_mm(130, ...)`
   return, and why is it EXTRAPOLATED? (Points available: 113 -> 37.5, 124 -> 87.5.)
