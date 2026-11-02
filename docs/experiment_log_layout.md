# Lab mix log: stable SI schema

Copy `experiments/mix_log_template.csv` and DELETE its two synthetic examples.
Record one row per mix per test age. Keep headers unchanged. Excel `.xlsx` and
UTF-8 CSV are supported; use ISO dates `YYYY-MM-DD`. Errors identify spreadsheet
row numbers (header=1) and columns. Invalid rows are excluded; valid rows remain
available. Review all errors before fitting. At least three eligible rows are
required, and their w/c values must vary for an Abrams fit.

| Column | What to record |
|---|---|
| mix_id | Stable unique mix/batch identifier, e.g. LAB-2026-001; reuse across ages. |
| material_set_id | Stable cement/aggregate/material-source set, e.g. LAU-CEM1-AGG1. Change it when materials change. Fit one set at a time. |
| cement_kg_m3 | Actual cement content, kg/m3. |
| water_kg_m3 | Actual added water, kg/m3; do not include aggregate free water twice. |
| ca_kg_m3, fa_kg_m3 | Coarse/fine mass, kg/m3, on the declared basis. |
| weight_basis | `oven_dry`, `ssd`, or `as_received`; one basis for both aggregates. |
| cement_sg | Dimensionless cement SG. |
| cement_type | I, II, III, IV or V. |
| ca_sg_ssd, fa_sg_ssd | Dimensionless bulk SSD SG; keep the mass/SG bases consistent. |
| ca_drd_kg_m3 | Coarse aggregate dry-rodded density, kg/m3. |
| ca_absorption_pct, fa_absorption_pct | Absorption as percent of OD mass (1 means 1%). |
| ca_mc_pct, fa_mc_pct | Total moisture as percent of OD mass, measured for that batch. |
| nmas_mm | Nominal maximum aggregate size, mm; distinguish from maximum size. |
| ca_shape | angular, subangular, gravel_with_crushed or round_gravel. |
| fa_fm | Dimensionless fine-aggregate fineness modulus. |
| air_pct | Measured air percent, required; the loader does not assume exposure air. |
| air_entrained | true/false (or 1/0), describing the mix. |
| curing | moist or steam; also document actual conditions in notes. |
| age_days | Test age in days, >=1. Default fit includes only exact 28-day rows. |
| specimen | cylinder_150x300 or cube_150. |
| n_specimens | Number of specimens averaged at this age; positive integer. |
| measured_strength_mpa | Arithmetic mean of valid specimen strengths, MPa. Retain individual results in the lab record. |
| strength_std_mpa | Optional sample standard deviation, MPa. Leave blank if unavailable; do not substitute zero for unknown. |
| measured_slump_mm | Measured slump, mm. |
| test_date | ISO calendar date of the test. |
| notes | Placement, curing, deviations, rejected specimens, lab record reference and other relevant conditions. |

Reserved accepted/ignored columns: `scm_name`, `scm_pct`, `scm_sg`, `sp_kg_m3`.
Nonempty reserved columns do not cause the current non-ML fit to model SCM or
superplasticizer effects; separate such materials and interpret fits accordingly.
Unknown extra columns are retained in the original source file but not modeled.

For cube measurements, add optional `cube_to_cylinder_factor`. It has no default.
The measured cube mean is multiplied by this explicit factor before fitting;
cube rows without it are errors. Confirm the factor with the professor.

`age_policy="convert"` divides a non-28-day measured mean by the literal age
factor to estimate its 28-day equivalent. Exact 28-day rows stay unchanged.
This is a model-based transformation with the same applicability assumptions as
the age equation, not an independent 28-day measurement. The UI reports excluded
or converted row counts. Avoid counting repeated ages of the same mix as
independent evidence without considering the experimental design.

Stored fits live in `calibrations/<material_set_id>.json`, with a `models` mapping
holding each model's constants, n, R2 space, R2 in MPa, RMSE in MPa, source
filename, exact source-byte SHA-256 and UTC creation time. Saving a model merges
it with other models for the same set. These are in-sample statistics, not
cross-validation or a claim that strength is certified. Keep training conditions
consistent, including AE status, and do not transfer fits to unrelated materials.
