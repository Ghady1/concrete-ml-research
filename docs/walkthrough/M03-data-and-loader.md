# M03 - Reference data (JSON) and tables/loader.py

## What this milestone adds

| File | Purpose |
|---|---|
| `src/concretecalc/data/*.json` (17 files) | Every reference number, typed only from task section 8 (+ D-1 rules/thresholds) |
| `src/concretecalc/tables/loader.py` | `load_series`, `load_grid`, `load_mapping`, `list_table_ids` |
| `docs/table_verification.md` | Checklist, row by row, for verifying each table against the slides and ACI/PCA |
| `tests/test_tables.py` (M3 section) | 73 tests |

## The 17 tables

| id | kind | what | used from |
|---|---|---|---|
| `wc_vs_strength` | series | w/c vs **required average** f'cr (non-AE, AE) | M4, M9 (aci_table model), M12 step 4 |
| `wc_vs_specified_fc` | series | w/c vs **specified** f'c (stored, not default; Q2) | M12 (shown + flagged) |
| `mixing_water` | grid2d | water kg/m3, rows = slump band midpoints, cols = NMAS | M4, M10, M12 |
| `mixing_water_slump_bands` | mapping | band edges 25-50 / 75-100 / 150-175 mm | M4 band reading (D-2) |
| `shape_reduction` | mapping | kg/m3 to subtract by aggregate shape | M4 |
| `air_content` | series | air % by NMAS: non-AE + AE mild/moderate/severe | M4, M11, M12 |
| `bulk_volume_ca` | grid2d | b/b0 by NMAS x FM | M4, M7, M12 |
| `unit_weight` | series | fresh concrete kg/m3 by NMAS (non-AE, AE) | M7, M12 |
| `slump_ranges` | mapping | min/max slump by element | M4, M10, M12 |
| `durability` | mapping | max w/c + min f'c (psi) per class; full-hydration w/c | M4, M9, M12 |
| `f_factor` | series | F by number of tests n | M8 |
| `min_cement_flatwork` | series | ACI 302 minimum cement by NMAS | M12 |
| `min_cement_misc` | mapping | severe exposure 334, underwater 385 | M12 |
| `age_coefficients` | mapping | a, b for moist/steam, Type I/III | M9 |
| `standard_sieves` | mapping | the 8 sieve sizes | M4, M12 |
| `required_strength_rules` | mapping | 1.34, 2.33, 3.45; 7.0/8.5/10.0 with band edges; n_min 15 | M8 (D-1) |
| `flag_thresholds` | mapping | placeholders, slide rules, soft/hard input limits | M5 onward (D-1) |

**Key naming in mappings.** A mapping holds one number per label, so multi-value tables use dotted
keys: `"beams_reinforced_walls.max_mm"`, `"moist.type_I.a_days"`, `"soft.cement_kg_m3.min"`.
The unit is in the key's suffix (ground rule 2).

**null vs 0.** The mixing-water table has no value at 150 mm NMAS for the 150-175 mm slump band.
It is stored as `null`, which becomes NaN, so a lookup that needs it reports `UNAVAILABLE`.
Writing `0` would silently mean "no water".

## loader.py, step by step
1. `_read_json(table_id)` opens `concretecalc/data/<id>.json` through
   `importlib.resources.files`. That works whether the package is installed in editable mode or
   from a wheel (checked: the wheel contains all 17 JSON files).
2. `_check_kind` refuses a table loaded with the wrong loader, e.g. `load_grid("f_factor")`.
3. `_build_meta` checks that all six meta keys exist and that `meta.id` equals the file name, so a
   copied file with a stale id is caught.
4. `_read_only_array` converts with `np.array(values, dtype=float)`. numpy turns `None` into NaN
   for float arrays, then the array is set to read-only.
5. The dataclasses from M1 then validate axes and shapes. A malformed table therefore fails on its
   first load.

**Why `@lru_cache`?** Tables are read once per process instead of on every lookup. There is one
consequence to know: everyone gets *the same object*. If someone could modify it, the change
would leak into every later lookup. Read-only arrays plus frozen dataclasses prevent most of
that. The dicts inside (`columns`, `variants`, `values`) are still technically mutable Python
dicts. Engine code never modifies them, and the walkthrough exercises show why it must not.

## Deviations from PLAN.md
- **New file `mixing_water_slump_bands.json`.** Needed by the D-2 band-reading option you
  approved. PLAN M3 listed 14 + 2 (D-1) files, so this makes 17. `model_constants.json`
  still arrives in M9 with the `presets` kind (D-3).
- **`flag_thresholds.json` also holds the soft/hard input limits of task section 5.** Ground
  rule 5 says all reference numbers live in JSON, and D-1 approved this file for thresholds.
  M5's `validation.py` will read them from here instead of hard-coding them.
- Range values that can be read off a table (strength 14-48 MPa, FM 2.40-3.00) are **not**
  duplicated in `flag_thresholds`. The code will take them from the table axes, so they can
  never disagree.

## Exercises
1. Open `mixing_water.json`. Which row/column holds 205 kg/m3? What is the midpoint of the
   75-100 mm band and where else in the data folder can that number be derived from? (Hint: a
   test checks it.)
2. In a Python shell, run `t = load_series("wc_vs_strength")` and then `t.x[0] = 15`. What
   happens and why? Then try `load_series("wc_vs_strength") is t`. Why is it `True`, and why is
   that only safe because of the previous answer?
3. Convert the freeze-thaw minimum strength from `durability.json` to MPa by hand with
   1 psi = 0.00689475729 MPa. Compare it with Example 2's specified f'c of 24.1 MPa: by how many
   MPa does it exceed it?
