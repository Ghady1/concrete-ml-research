# M05 - SI inputs and explicit validation

The frozen dataclasses in `schemas.py` describe a batch without performing
calculations. `aggregate_weight_basis` has no default: callers must state whether
the aggregate masses are oven dry, SSD or as received. `binders()` returns cement
first, followed by SCMs. `DISCLAIMER` provides the shared research prediction label.

Call `validate_mode_b()` or `validate_mode_a()` before calculations. Invalid input
raises `ValueError` naming the field. Warnings are returned as frozen `Flag` data.
No input is corrected silently. All task soft limits and moisture hard bounds
come through the lookup layer from `flag_thresholds.json`. Batch mass soft limits
are checked after dividing by the declared volume; entered masses stay unchanged.

## Three hand exercises

1. A 0.1 m3 batch with cement 35 kg and water 18 kg represents 350 and
   180 kg/m3. Neither mass gets a soft warning. Check that validating this batch
   returns the same flags as its 1 m3 equivalent.
2. SSD aggregate with absorption 1% and entered MC 2% gets
   `SSD_MC_MISMATCH_COARSE` (or `_FINE`). Validation preserves both numbers;
   M06 will use absorption as the effective MC on the SSD basis.
3. NMAS 22 mm and FM 3.2 give `NONSTANDARD_NMAS` and `FM_EXTRAPOLATION`.
   FM 3.2 is inside the broad 2.0-3.5 soft range, but outside the b/b0 table's
   2.4-3.0 axis. These warnings describe different applicability checks.

## Flag codes

`SOFT_LIMIT_*` names cement, cement SG, water, air, age, each aggregate's SG,
absorption and MC, coarse DRD, fine FM, and Mode A b/b0 adjustment.
Other codes are `NONSTANDARD_NMAS`, `FM_EXTRAPOLATION`,
`CEMENT_TYPE_APPROXIMATION`, `CUBE_FACTOR_MISSING`, `SCM_NOT_SUPPORTED`,
`SSD_MC_MISMATCH_COARSE`, `SSD_MC_MISMATCH_FINE`,
`SUPERPLASTICIZER_NOT_MODELED`, and `WATER_REDUCER_NOT_MODELED`.
`flags_from_lookup()` preserves table messages and uses warning severity for
clamping/extrapolation and error severity for unavailable data.

## Scope and verification

Unit conversion functions and property tests already existed from M04 and are
retained. Added input-boundary tests cover batch normalisation, nested materials,
required aggregate basis, immutable inputs, geometry, optional admixtures and
structured flags. No calculation workflow or strength prediction is added here.
Assumption A-45 records additional mathematical boundary checks. No new professor
questions or reference values were introduced.

Full suite: **446 passed**, Python 3.12. The original Python 3.10.0 environment
hit a pytest internal error; verification used an isolated temporary Python 3.12
environment with the project installed editable plus dev dependencies and pandas
(needed by the owner's baseline tests). Windows denied access to an old pytest
temporary directory, so the suite used a fresh `--basetemp` directory. Neither
workaround changes calculation code or project dependency declarations.
