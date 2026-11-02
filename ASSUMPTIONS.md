# ASSUMPTIONS.md

Every choice not dictated by the task text. Each one is a default the owner can overturn. "Q" numbers point to OPEN_QUESTIONS.md.

## Repo / tooling
- **A-33** The owner chose (2026-11-01) to work on branch `claude/loving-allen-8w5d2q`, pushed after each milestone, instead of a local `build-engine`. `src/concretecalc/` lives beside the owner's `src/concrete_ml/`.
- **A-35** `pyproject.toml`: setuptools backend; distribution name `concrete-ml-research`; package discovery under `src/` installs both `concretecalc` and the owner's `concrete_ml` (so `tests/test_engineering.py` runs). The owner's `requirements.txt` is not referenced. `ucimlrepo`/`pandas` used by `concrete_ml/data/ingest.py` are not added to pyproject.
- **A-07** Architecture test scope: no `streamlit`/`matplotlib` import anywhere under `src/` (both packages). Inside `src/concretecalc`, `pandas`/`openpyxl` are allowed only in `calibration/dataset.py`. The owner's `concrete_ml/data/ingest.py` (pandas) is outside that rule.
- **A-22** The Streamlit AppTest smoke test uses `pytest.importorskip("streamlit")`, so `pip install -e ".[dev]"` alone still gives a green suite. It runs once the `app` extra is installed.

## Data layer
- **A-01** `worst()` with no arguments returns `Status.OK`.
- **A-02** `interp1d` with fewer than 2 non-NaN points returns `Lookup(None, UNAVAILABLE, ...)` instead of raising, because it is a data gap, not a programming error. Malformed tables still raise at load time.
- **A-03** Labelled multi-value tables (slump ranges, durability, age coefficients, min cement) are stored as `mapping` with dotted keys, e.g. `"beams_reinforced_walls.max_mm"`. The +25 mm hand-consolidation allowance is stored as `"mass_concrete.hand_consolidation_extra_mm"`.
- **A-04** Unit-conversion factors are exact definitions, not empirical reference data, so they are module constants in `units.py` (values from task section 8).
- **A-05** `min_cement_flatwork_kg_m3` interpolates linearly between listed NMAS values. Above 37.5 mm (no data) it returns UNAVAILABLE and Mode A applies no flatwork minimum, with a flag (Q19).
- **A-39** Band edges of the mixing-water table are stored in `mixing_water_slump_bands.json` (needed for the D-2 band option); soft/hard input limits of task section 5 are stored in `flag_thresholds.json` (D-1). Ranges that can be read from a table axis (strength 14-48 MPa, FM 2.40-3.00) are taken from the table, not duplicated.
- **A-40** `interp1d` drops a pair when either xs or ys is NaN (the PLAN wording said ys only); needed for table inversion, identical otherwise.
- **A-41** Band reading of the mixing-water table (D-2): a slump inside a band (edges included) uses that band's row; between two bands, linear between the upper edge of the lower band and the lower edge of the upper band; outside 25-175 mm the end band is used with status CLAMPED (even with policy "extrapolate": extrapolating a band has no meaning); "raise" raises.
- **A-42** `slump_for_water_mm` and `bulk_volume_ratio` apply their single `policy` to both axes (NMAS and water / NMAS and FM).
- **A-43** `max_wc_durability("none")` and `min_fc_durability_mpa("none")` return `Lookup(None, OK)`: "no limit" is not missing data.
- **A-44** `min_cement_flatwork_kg_m3` clamps below 9.5 mm (no smaller sieve in scope).
- **A-24** `TableMeta.units` is a `dict[str, str]` and `notes` is a single string.
- **A-38** `Status` member values are lowercase strings ("ok", "clamped", ...).
- **A-23** Enumerations are `typing.Literal` string types validated at runtime, not Enum classes (simpler for the owner). `Status` stays an Enum as the task specifies.

## Inputs / validation
- **A-45** Validation rejects infinite values as well as NaN, nonpositive FM/DRD/NMAS, negative optional admixture doses, air >=100%, and water reduction >=100%. These are mathematical input boundaries, not new empirical limits. FM outside the lookup axis gets `FM_EXTRAPOLATION`; outside the broader task soft range also gets `SOFT_LIMIT_FINE_FM`.
- **A-06** Mode A accepts an `nmas_mm` override. If the override and all four geometry inputs are missing, `ValueError`. If the override is given, step 2 is reported as "user-specified".
- **A-30** `exposure` is a required Mode B field (it is needed for the default AE air content). It is ignored for non-AE mixes.
- **A-31** With `batch_volume_m3`, every mass (cement, water, aggregates, SCM) is divided by the batch volume. `air_pct` is unchanged (already per volume).
- **A-37** Basis = ssd: per the task, effective MC := Abs and free water = 0. A flag is raised if the entered MC differs from Abs.
- **A-08** The basis-invariance property is tested between oven_dry and as_received for any MC. The ssd basis joins the comparison only when MC == Abs, because entering weights "on SSD basis" means the aggregate is at SSD.
- **A-11** Sigma given but n missing: F = 1.00 (as if n >= 30) + warning flag (Q31).

## Mode B physics
- **A-47** Mode B air-entrainer dosage is reported for AE mixes only. It uses an explicitly supplied rate or otherwise the JSON slide rate, always with the product-specific warning. A partial model-constants mapping overrides only named models; unknown model keys raise. Nonpositive effective water after absorption raises instead of feeding an invalid ratio to strength models. Plot curves use the model's extrapolated research curve independently of the report's table policy.
- **A-26** No extra air term in Abrams/Bolomey (to avoid double counting). AE vs non-AE use separate constant sets / the AE table column. Feret is the explicit air-aware model. (Required by the task to be logged.)
- **A-09** CA void content uses SG_OD = SG_SSD / (1 + Abs/100) (Q22).
- **A-10** Flag thresholds are placeholders (Q15): volume closure |e| > 0.02 m3 warning, > 0.05 m3 error; unit weight deviation > 5 %; b/b0 deviation > +-10 %; model spread > 5 MPa; slump band +-25 mm.
- **A-15** The `aci_table` model raises an info flag when NMAS is outside 19-25 mm, because the table is stated for 19-25 mm aggregate (Q24).
- **A-17** Plot curves are sampled at w/c 0.25 to 0.85 in steps of 0.01 (61 points).
- **A-18** Predictions are cylinder-basis. For `cube_150` with a user factor, the report also gives the cube equivalent = cylinder / factor (Q27).
- **A-36** The age-equation validity flag (20-70 MPa) is checked on each model's predicted 28-d mean.
- **A-14** Feret default K is fitted to the w/c table points using water 205/184 kg/m3 (non-AE/AE), air 2.0/5.0 %, cement SG 3.15, C = W/wc (Q23).
- **A-34** Abrams and Bolomey have separate non-AE and AE constant sets. Feret has one K for both (it carries air explicitly).
- **A-12** Inverse required strength, sigma unknown: in either gap ([28, 29.5) or (43.5, 45]) take the lower of the two adjacent-band candidates + flag (Q21).

## Mode A
- **A-48** Geometric maximum-size factors from original task section 7 are stored in the existing numeric-rules JSON (`flag_thresholds`) rather than code. `design_mix` propagates policy through private helpers, retaining approved step signatures. A nonpositive remaining fine volume raises; a below-table geometric size returns the specified fallback plus an error flag. The weight-method difference is weight-method FA minus volume-method FA.
- **A-19** Water reducer: mixing water x (1 - water_reducer_pct/100).
- **A-20** Moisture conventions in Mode A: course (slides) applies the slide formulas to CA_dry and FA_ssd as they come out of steps 6-7. Strict uses CA_ssd = CA_dry(1+Abs/100) and FA_ssd. Both are always computed and reported (Q25).
- **A-27** Fine aggregate by absolute volume on the SSD basis (SSD mass with SSD SG). The weight method is reported alongside for comparison. (Required by the task to be logged.)
- **A-28** The 334 kg/m3 minimum applies when exposure == "severe". 385 kg/m3 applies when underwater. The flatwork table applies when flatwork. The governing minimum is the largest applicable one.
- **A-29** NMAS rule "3/4 of smallest clear rebar spacing (or cover)" = 0.75 x min(given spacing, given cover). The governing limit is the smallest of all given limits.

## Calibration
- **A-49** Calibration rows always supply measured air, so an internal exposure placeholder is never used to look up air. Optional extra `cube_to_cylinder_factor` is accepted per M14/Q4; missing cube factors reject rows. Error row numbers include the header. ISO dates and true/false or 1/0 booleans are accepted; Excel date cells are converted to ISO dates. One file per material set stores a `models` mapping of the specified per-model payloads. Non-28d conversion uses the literal age factor and leaves actual 28d measurements unchanged. A fit cannot pool different material_set_id values. Only `.xlsx` Excel is supported by the approved openpyxl dependency (legacy `.xls` needs conversion to `.xlsx` or CSV).
- **A-46** R2 for constant measured strengths is reported as 1 for zero residual and 0 otherwise (avoids an undefined division). Fitting rejects nonfinite/nonpositive rows, constant w/c for Abrams, and Abrams B<=1. Preset dictionaries are read fresh so a caller cannot mutate another prediction's defaults. Seven-day presets cannot generate 28-day means (approved D-4).
- **A-13** The numpy-only fit functions (`calibration/fit.py`) are created in M9, because the default constants must be produced and re-verified by them. Dataset/store come in M14.
- **A-21** `created_utc` is supplied by the caller (UI/store boundary) so that fit functions stay pure.

## Tests / files
- **A-50** UI exports remain explicitly SI-labelled even when viewing US units. Actual-batch entries convert kg/lb and m3/yd3; per-volume contents convert kg/m3 and lb/yd3. Missing adapter keys use SI defaults; only explicitly supplied display-unit values are converted. Numeric widget values are converted on unit-system changes. The sidebar moisture convention applies to Mode A; Mode B uses the explicit aggregate basis.
- **A-16** Slump tests go in a new `tests/test_slump.py` (not in the task's allowed list; D-6).

## Studio 2.0 decisions (2026-11-02)

- Intended yield remains declared, not automatically rebalanced. Computed density
  is mass per declared volume and is not labelled a measured fresh density.
- Workability from the inverse mixing-water table is heuristic. Placeholder
  bounds remain in raw data for compatibility, not as confidence/accuracy claims.
- Optional internal holdout requires at least 10 distinct mix IDs and holds out
  max(2, floor(n_groups/5)) IDs, ordered by SHA-256 of `15:<mix_id>`. This is a
  project sufficiency guard, not a validated sample-size recommendation. Mixing
  repeated ages/specimens across train/test is prohibited. External validation
  and repeated-fold cross-validation are not implemented in this phase.
- New web fits require one air condition, cement type and curing condition per
  material set. Recorded conditions are enforced on use; legacy files without
  context remain readable. Selected-model replacement retains unselected models,
  with each model retaining its own source/context.
- Notebook persistence is opt-in local browser storage; lab upload bytes/rows are
  not stored there. Version fingerprints identify runtime/data/parameters but
  do not embed the software or certify correctness; retain the matching checkout.
