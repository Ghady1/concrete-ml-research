# PLAN.md - `concretecalc` build plan (Phase 1, awaiting owner approval)

Status: DRAFT for approval. Nothing below M0 is implemented yet.
Read together with CLAUDE.md (ground rules), ASSUMPTIONS.md (A-numbers) and OPEN_QUESTIONS.md (Q-numbers).

## 0. Phase 0 findings (repo inspection, 2026-11-01)

| Item | Expected (task section 3) | Found | Action |
|---|---|---|---|
| pyproject.toml | present | **missing** | Created in M0 (numpy core; extras dev/calibration/app; package-data `data/*.json`). |
| src/concretecalc/ | empty skeleton | **missing** | Created in M0 (only `__init__.py` with a docstring). Rest is created milestone by milestone. |
| src/concrete_ml/ | - | owner package: `features/engineering.py` (owner code), `data/ingest.py` (owner code, pandas + ucimlrepo), many empty files | **Untouched baseline.** Installed by the same pyproject so `tests/test_engineering.py` runs in the full suite. |
| tests/ | conftest + test files | only `tests/test_engineering.py` (owner code, 4 tests) | Owner file untouched. Empty `tests/conftest.py` added in M0. |
| app/streamlit_app.py | empty | empty | Filled in M15. |
| docs/ | slides PDF, walkthrough/, ... | `data_dictionary.md`, `methodology.md`, `research_questions.md` (all empty); **no CIE308_Ch4_PartB.pdf** | Table cross-check against the slides is NOT possible; `docs/table_verification.md` (M3) will be a checklist for the owner. Owner's empty docs untouched. |
| requirements.txt | - | owner's `pip freeze` (UTF-16 LE, CRLF; pins numpy 2.5.4, pandas 3.0.6, pytest 9.1.1, ucimlrepo) | Untouched. Not used by pyproject (pip can read the UTF-16 BOM; just FYI). |
| data/metadata/sources.csv | - | empty | Untouched (different from `src/concretecalc/data/`). |
| test-push.md | - | from the earlier push test | Left as is; owner may delete it. |
| Git | branch `build-engine` | owner chose `claude/loving-allen-8w5d2q`, pushed after each milestone | See CLAUDE.md. |

M0 verification (Linux container, Python 3.13): `python -m venv .venv; pip install -e ".[dev]"` OK;
`pytest` -> 4 passed (owner tests). Owner should re-run on Windows (commands in CLAUDE.md).

## 1. Architecture (target)

```
app/ (Streamlit, M15)  --->  app/adapters.py (pure: widgets <-> dataclasses, unit conversion)
                                   |
                                   v
src/concretecalc/   (numpy only; NO streamlit/matplotlib; pandas only in calibration/dataset.py)
  schemas.py      input dataclasses, Literal types, DISCLAIMER
  validation.py   hard limits (ValueError) + soft limits (Flag)
  flags.py        Flag dataclass + helpers
  units.py        exact conversion factors (boundary use only)
  tables/         models -> interpolate -> loader -> lookups   (engine calls ONLY lookups)
  moisture.py  volumes.py  slump.py  required_strength.py
  strength/       registry (interface) + aci_table, abrams, bolomey, feret, age
  mode_b.py       Mode B orchestrator -> StrengthReport
  mix_design.py   Mode A (ACI 211.1 steps 1-10) -> MixDesignReport (+ to_mode_b_inputs)
  calibration/    fit (numpy), store (json), dataset (pandas)
  data/*.json     all reference numbers
```
Dependency direction is one-way: lookups <- step modules <- orchestrators <- app. No module imports an orchestrator.

Conventions used in every milestone:
- Enumerations are `typing.Literal[...]` string types (simple to explain; validated at runtime by `validation.py`).
- Every result dataclass is `@dataclass(frozen=True)`; array-holding ones add `eq=False`.
- Every function that can go out of a table range returns/propagates `Status` + `Flag`s; nothing prints.
- `Policy = Literal["clamp", "extrapolate", "raise"]` is the single out-of-range control.

---

## M0 - Baseline (THIS milestone; Phase 1 ends here)
Files: `pyproject.toml`, `src/concretecalc/__init__.py` (docstring only), `tests/conftest.py` (empty), `CLAUDE.md`, `PLAN.md`, `OPEN_QUESTIONS.md`, `ASSUMPTIONS.md`.
Acceptance: `pip install -e ".[dev]"` and `pytest` succeed (done: 4 passed). Owner replies "approved" (with edits).

## M1 - tables/models.py
Files: `src/concretecalc/tables/__init__.py`, `tables/models.py`, `tests/test_tables.py` (models part).
Signatures:
```python
class Status(str, Enum): OK="ok"; CLAMPED="clamped"; EXTRAPOLATED="extrapolated"; UNAVAILABLE="unavailable"
def worst(*statuses: Status) -> Status            # severity OK<CLAMPED<EXTRAPOLATED<UNAVAILABLE; no args -> OK (A-01)
@dataclass(frozen=True) class Lookup: value: float | None; status: Status; warnings: tuple[str, ...] = ()
@dataclass(frozen=True) class TableMeta: id: str; title: str; source: str; verified_against_primary: bool; units: dict[str, str]; notes: str
@dataclass(frozen=True, eq=False) class Series1D: meta: TableMeta; x: np.ndarray; columns: dict[str, np.ndarray]
@dataclass(frozen=True, eq=False) class Grid2D:   meta: TableMeta; rows: np.ndarray; cols: np.ndarray; variants: dict[str, np.ndarray]
@dataclass(frozen=True) class LabelMap: meta: TableMeta; values: dict[str, float]
```
`__post_init__`: axes 1-D, >= 2 points, strictly increasing (NaN in an axis = invalid); each column shape == x.shape; each variant shape == (len(rows), len(cols)); LabelMap non-empty. Raise `ValueError` with the table id.
Tests: worst() ordering incl. all pairs; Lookup defaults; each invalid case raises (2-D axis, 1 point, equal points, decreasing, NaN axis, wrong column length, wrong variant shape); valid tables construct; NaN allowed in column values.
Acceptance: tests pass; no numpy besides `np.ndarray` checks.

## M2 - tables/interpolate.py
Files: `tables/interpolate.py`, `tests/test_tables.py` (interpolation part, + hypothesis).
```python
Policy = Literal["clamp", "extrapolate", "raise"]
class OutOfRangeError(ValueError)
def _bracket(v: float, axis: np.ndarray, policy: Policy, label: str) -> tuple[int, float, Status, tuple[str, ...]]
def interp1d(x: float, xs: np.ndarray, ys: np.ndarray, policy: Policy, label: str) -> Lookup
def interp2d(r: float, c: float, rows: np.ndarray, cols: np.ndarray, grid: np.ndarray,
             policy: Policy, row_label: str, col_label: str) -> Lookup
```
Equations: i0 = clip(searchsorted(axis, v, "right") - 1, 0, n-2); t = (v - axis[i0]) / (axis[i0+1] - axis[i0]); 1-D value = y0 + t(y1 - y0); 2-D weights = outer([1-tr, tr], [1-tc, tc]), value = sum(w * corners) over corners with w != 0.
Behaviour: NaN query -> ValueError; outside range: raise -> OutOfRangeError, clamp -> clipped + CLAMPED, extrapolate -> end segment + EXTRAPOLATED; warning text = "<label>=<v> outside table range [<lo>, <hi>] (<status>)". interp1d drops NaN ys first, then sorts by xs (allows inversion: xs may be a decreasing column), needs >= 2 remaining strictly increasing xs else Lookup(None, UNAVAILABLE) (A-02). interp2d: any needed corner NaN -> Lookup(None, UNAVAILABLE, warning); status = worst(row status, col status).
Tests: exact nodes (1-D, 2-D); midpoints; below/above under each policy (value, status, message contains label and range); exact end nodes are OK (not clamped); NaN query raises; NaN ys dropped; decreasing ys inverted via sort; < 2 points -> UNAVAILABLE; 2-D null corner with zero weight is fine (on a node) and with non-zero weight -> UNAVAILABLE; hypothesis: value of a linear function is reproduced exactly (rel 1e-12) for any in-range query; interpolated value lies between bracket ys.

## M3 - JSON data files + tables/loader.py
Files: `src/concretecalc/data/*.json` (14 files below), `tables/loader.py`, `tests/test_tables.py` (loader part), `docs/table_verification.md` (checklist: each table, each value, slide page, ACI/PCA page, verified-by, date; all unchecked).
```python
@lru_cache(maxsize=None) def load_series(table_id: str) -> Series1D
@lru_cache(maxsize=None) def load_grid(table_id: str) -> Grid2D
@lru_cache(maxsize=None) def load_mapping(table_id: str) -> LabelMap
def list_table_ids() -> tuple[str, ...]
```
Reads `importlib.resources.files("concretecalc") / "data" / f"{table_id}.json"`, checks `kind`, converts with `np.array(..., dtype=float)` (null -> NaN), sets `arr.flags.writeable = False`, checks meta.id == file name.
All files: meta.source = "CIE308 Ch4 Part B slides (Dr. M. Tawk), after ACI 211.1; verify against ACI 211.1-91 and PCA Design and Control of Concrete Mixtures" (except model_constants, see M9), `verified_against_primary: false`.

| file | kind | axes | content (section 8 only) |
|---|---|---|---|
| wc_vs_strength | series | x = f'cr MPa [14,21,28,35,41,48] | non_ae [.82,.68,.57,.48,.41,.33]; ae [.74,.59,.48,.40,.32,null] |
| wc_vs_specified_fc | series | x = f'c MPa [17,21,24,28,31] | non_ae [.67,.58,.51,.44,.38]; ae [.54,.46,.40,.35,null] |
| mixing_water | grid2d | rows = slump midpoints [37.5,87.5,162.5]; cols = NMAS | variants non_ae, ae (values as section 8; null at 150 mm / 150-175); notes give band labels |
| shape_reduction | mapping | - | angular 0, subangular 12, gravel_with_crushed 21, round_gravel 27 |
| air_content | series | x = NMAS | non_ae, ae_mild, ae_moderate, ae_severe |
| bulk_volume_ca | grid2d | rows = NMAS; cols = FM [2.40,2.60,2.80,3.00] | variant b_b0 |
| unit_weight | series | x = NMAS | non_ae, ae |
| slump_ranges | mapping | - | "<element>.max_mm"/"<element>.min_mm" for 6 elements + "mass_concrete.hand_consolidation_extra_mm" 25 (A-03) |
| durability | mapping | - | "<class>.max_wc", "<class>.min_fc_psi" for 3 classes; "full_hydration.min_wc_lower" 0.22, "...upper" 0.25 |
| f_factor | series | x = n [15,20,25,30] | F [1.16,1.08,1.03,1.00] |
| min_cement_flatwork | series | x = NMAS [9.5,12.5,19,25,37.5] | min_cement_kg_m3 [360,350,320,310,280] |
| min_cement_misc | mapping | - | severe_exposure 334, underwater 385 |
| age_coefficients | mapping | - | "moist.type_I.a_days" 4.0, "moist.type_I.b" 0.85, "moist.type_III..." 2.3/0.92, "steam.type_I..." 1.0/0.95, "steam.type_III..." 0.7/0.98 (source: ACI 209R-92) |
| standard_sieves | mapping | - | "9.5":9.5 ... "150":150 (8 sieves) |
| model_constants | see M9 | | written in M9, not M3 |

Tests: every file loads with the right loader; wrong loader -> ValueError (kind check); arrays read-only (assignment raises); every meta.source non-empty; every verified_against_primary is False; null -> NaN in the right cells; spot values per table (one per row/variant); `list_table_ids()` equals the set of files; lru_cache returns the same object.
**Decision needed D-1 (see OPEN_QUESTIONS.md Part B):** ground rule 5 says ALL reference numbers live in JSON. Section 8 / 6 also contain numeric rules not covered by the allowed file list: f'cr equation constants (1.34, 2.33, 3.45), unknown-sigma margins (7.0/8.5/10.0 and band edges 21/35), slide rules (25 mm per 6 kg/m3; 6.3 ml), validity ranges (age 20-70 MPa; w/c 0.25-0.85), flag thresholds. Proposal: add two files `required_strength_rules.json` (mapping) and `flag_thresholds.json` (mapping, incl. slide rules and all A-xx thresholds). Fallback if you say no: named module-level constants with source docstrings. Unit-conversion factors stay as exact constants in `units.py` (they are definitions, not reference data; A-04).

## M4 - tables/lookups.py
Files: `tables/lookups.py`, `tests/test_tables.py` (lookups part).
```python
def wc_for_strength(fcr_mpa: float, air_entrained: bool, policy: Policy = "extrapolate") -> Lookup
def strength_for_wc(wc: float, air_entrained: bool, policy: Policy = "extrapolate") -> Lookup          # value = f'cr MPa (inverse, same table)
def wc_for_specified_fc(fc_mpa: float, air_entrained: bool, policy: Policy = "extrapolate") -> Lookup  # stored table, not default
def mixing_water_kg_m3(slump_mm: float, nmas_mm: float, air_entrained: bool, shape: AggregateShape, policy: Policy = "clamp") -> Lookup
def slump_for_water_mm(water_kg_m3: float, nmas_mm: float, air_entrained: bool, shape: AggregateShape, policy: Policy = "extrapolate") -> Lookup
def shape_reduction_kg_m3(shape: AggregateShape) -> Lookup
def air_content_pct(nmas_mm: float, exposure: Exposure | None, air_entrained: bool, policy: Policy = "clamp") -> Lookup
def bulk_volume_ratio(nmas_mm: float, fm: float, policy: Policy = "extrapolate") -> Lookup
def fresh_unit_weight_kg_m3(nmas_mm: float, air_entrained: bool, policy: Policy = "clamp") -> Lookup
def slump_limits_mm(element: ElementType) -> tuple[Lookup, Lookup]                                  # (min, max)
def f_factor(n_samples: int) -> Lookup                       # n < 15 -> UNAVAILABLE; n >= 30 -> 1.00 status OK
def max_wc_durability(durability_class: DurabilityClass) -> Lookup        # "none" -> Lookup(None, OK)
def min_fc_durability_mpa(durability_class: DurabilityClass) -> Lookup    # psi * 0.00689475729
def min_cement_flatwork_kg_m3(nmas_mm: float) -> Lookup                   # NMAS > 37.5 -> UNAVAILABLE (A-05)
def min_cement_misc_kg_m3(condition: Literal["severe_exposure", "underwater"]) -> Lookup
def standard_sieves_mm() -> tuple[float, ...]
def is_standard_nmas(nmas_mm: float) -> bool
```
Equations: mixing water = interp2d(slump midpoint axis, NMAS axis) - shape reduction. slump_for_water: for each midpoint row r, w_r = interp over NMAS at that row (skip UNAVAILABLE), subtract shape reduction, then interp1d(water -> slump midpoint). strength_for_wc: interp1d(x=wc column, y=f'cr) - NaN rows dropped, sorted ascending by w/c.
Tests (required by task): (87.5, 19, non-AE, angular) = 205; (87.5, 22, non-AE, angular) = 199 (t=0.5 between 205 and 193); subangular subtracts 12; (162.5, 150, non-AE) -> UNAVAILABLE; wc_for_strength(45, AE) EXTRAPOLATED (AE 48 row dropped); inverse round trip: strength_for_wc(wc_for_strength(f)) == f (abs 1e-9) at nodes and off-node; slump_for_water inverts mixing_water at the 3 midpoints (abs 1e-9); f_factor(17) = 1.128 (abs 1e-12), f_factor(40) = 1.0 OK, f_factor(10) UNAVAILABLE; air_content(19, moderate, AE) = 5.0; bulk_volume_ratio(37.5, 2.6) = 0.73, (19, 2.7) = 0.63, FM 3.2 EXTRAPOLATED; unit weight (19, AE) = 2276; min_fc_durability(freeze_thaw_moist) = 31.026 MPa; min cement flatwork 50 mm UNAVAILABLE.
**Decision needed D-2 (Q9, Q26):** with midpoint interpolation, a slump target of 75 mm (the table maximum for most elements = default Mode A target) gives non-AE 19 mm water = 190 + 0.75*(205-190) = **201.25 kg/m3**, whereas reading the "75-100 mm" band row gives **205**. The instructor's solutions almost certainly read the band (205). Options: (a) keep pure midpoint interpolation everywhere (task spec), (b) add `slump_lookup: Literal["interpolate","band"]` to `mixing_water_kg_m3` and default Mode A to "band", Mode B slump estimate stays interpolated. I recommend (b) but will not add it without approval.

## M5 - units.py, schemas.py, validation.py, flags.py
Files: those 4 + `tests/test_units.py`, `tests/test_validation.py`, (`tests/test_architecture.py` was moved forward to the M3 follow-up).
units.py (exact definitions, section 8):
```python
KG_PER_LB = 0.45359237; MM_PER_IN = 25.4; M_PER_YD = 0.9144; MPA_PER_PSI = 0.00689475729
KG_M3_PER_PCF = 16.01846337; M3_PER_YD3 = 0.764554857984; KG_M3_PER_LB_YD3 = KG_PER_LB / M3_PER_YD3
def lb_to_kg(mass_lb: float) -> float;            def kg_to_lb(mass_kg: float) -> float
def in_to_mm(length_in: float) -> float;          def mm_to_in(length_mm: float) -> float
def psi_to_mpa(stress_psi: float) -> float;       def mpa_to_psi(stress_mpa: float) -> float
def pcf_to_kg_m3(density_pcf: float) -> float;    def kg_m3_to_pcf(density_kg_m3: float) -> float
def lb_yd3_to_kg_m3(content_lb_yd3: float) -> float; def kg_m3_to_lb_yd3(content_kg_m3: float) -> float
def yd3_to_m3(volume_yd3: float) -> float;        def m3_to_yd3(volume_m3: float) -> float
```
flags.py:
```python
Severity = Literal["info", "warning", "error"]
@dataclass(frozen=True) class Flag: code: str; severity: Severity; message: str
def flags_from_lookup(lookup: Lookup, code: str) -> tuple[Flag, ...]   # CLAMPED/EXTRAPOLATED -> warning, UNAVAILABLE -> error, one Flag per warning string
def count_by_severity(flags: tuple[Flag, ...]) -> dict[str, int]
```
Flag codes are UPPER_SNAKE strings documented in docs/walkthrough/M05 (e.g. SOFT_LIMIT_CEMENT, NEGATIVE_FREE_WATER, VOLUME_CLOSURE, SCM_NOT_SUPPORTED, ...).
schemas.py:
```python
DISCLAIMER: str = "Estimated mean strength (research prediction; NOT a certified structural design value)..."
AggregateShape = Literal["angular", "subangular", "gravel_with_crushed", "round_gravel"]
Exposure = Literal["mild", "moderate", "severe"];  Curing = Literal["moist", "steam"]
CementType = Literal["I", "II", "III", "IV", "V"];  WeightBasis = Literal["oven_dry", "ssd", "as_received"]
Specimen = Literal["cylinder_150x300", "cube_150"];  MoistureConvention = Literal["course", "strict"]
DurabilityClass = Literal["none", "low_permeability", "freeze_thaw_moist", "corrosion_protection"]
ElementType = Literal["reinforced_foundation_walls_footings", "plain_footings_caissons_substructure_walls",
                      "beams_reinforced_walls", "building_columns", "pavements_slabs", "mass_concrete"]
@dataclass(frozen=True) class Binder: name: str; weight_kg: float; sg: float; kind: Literal["cement", "scm"]
@dataclass(frozen=True) class CoarseAggregateProperties: sg_ssd: float; drd_kg_m3: float; absorption_pct: float; mc_pct: float; shape: AggregateShape
@dataclass(frozen=True) class FineAggregateProperties:   sg_ssd: float; absorption_pct: float; mc_pct: float; fm: float
@dataclass(frozen=True) class Admixtures: air_entrainer_ml_per_pct_per_100kg: float | None = None; water_reducer_pct: float | None = None; superplasticizer_kg: float | None = None
@dataclass(frozen=True) class MixInputs:          # Mode B
    cement: Binder; water_kg: float; coarse_kg: float; coarse: CoarseAggregateProperties
    fine_kg: float; fine: FineAggregateProperties; nmas_mm: float
    aggregate_weight_basis: WeightBasis           # required, no default (task section 5)
    air_entrained: bool; exposure: Exposure
    cement_type: CementType = "I"; cement_strength_class: str | None = None
    air_pct: float | None = None                  # None -> ACI air table
    curing: Curing = "moist"; age_days: float = 28.0; batch_volume_m3: float | None = None
    specimen: Specimen = "cylinder_150x300"; cube_to_cylinder_factor: float | None = None
    sigma_mpa: float | None = None; n_samples: int | None = None; element: ElementType | None = None
    admixtures: Admixtures = Admixtures(); scm: tuple[Binder, ...] = ()
@dataclass(frozen=True) class ModeAInputs:
    specified_fc_mpa: float; element: ElementType; exposure: Exposure; air_entrained: bool
    cement_sg: float; coarse: CoarseAggregateProperties; fine: FineAggregateProperties
    sigma_mpa: float | None = None; n_samples: int | None = None; slump_target_mm: float | None = None
    hand_consolidated: bool = False; nmas_mm: float | None = None   # override of step 2 (A-06)
    form_min_dimension_mm: float | None = None; rebar_clear_spacing_mm: float | None = None
    cover_mm: float | None = None; slab_thickness_mm: float | None = None
    durability_class: DurabilityClass = "none"; underwater: bool = False; flatwork: bool = False
    cement_type: CementType = "I"; curing: Curing = "moist"; water_reducer_pct: float | None = None
    moisture_convention: MoistureConvention = "course"; bb0_adjustment_factor: float = 1.0; batch_volume_m3: float = 1.0
def binders(inputs: MixInputs) -> tuple[Binder, ...]          # cement first, then scm
```
validation.py:
```python
def validate_mode_b(inputs: MixInputs) -> tuple[Flag, ...]     # raises ValueError on hard limits; returns soft-limit flags
def validate_mode_a(inputs: ModeAInputs) -> tuple[Flag, ...]
```
Hard: weights <= 0 (cement, water, aggregates), SG <= 0, absorption outside 0-20, MC outside 0-30, age < 1, batch volume <= 0, unknown Literal value, cement Binder kind != "cement", cube factor <= 0, sigma < 0, n < 1, NaN anywhere. Soft (per m3 after normalisation for the masses): exactly the ranges in task section 5; plus off-node NMAS, FM outside 2.40-3.00 (b/b0 extrapolation), cement type II/IV/V (Type I age coefficients), SCM present, superplasticizer set, water reducer set in Mode B, cube without factor, SSD basis with MC != Abs.
Tests: every conversion vs a hand value + round trip (hypothesis, rel 1e-12); lb/yd3 factor = 0.593276 (abs 1e-6); each hard limit raises with a message naming the field; each soft limit yields exactly one flag with the expected code; Binder shape (`scm` default empty, `binders()` order); MixInputs has no default for `aggregate_weight_basis` (constructing without it is a TypeError); test_architecture: AST-scan every `.py` under `src/` - no `streamlit`/`matplotlib` import; under `src/concretecalc` `pandas`/`openpyxl` only in `calibration/dataset.py` (the owner's `concrete_ml/data/ingest.py` is outside this rule, A-07).

## M6 - moisture.py
Files: `moisture.py`, `tests/test_moisture.py`.
```python
@dataclass(frozen=True) class AggregateMoisture:
    label: str; entered_kg: float; basis: WeightBasis; oven_dry_kg: float; ssd_kg: float
    effective_mc_pct: float; free_water_kg: float; flags: tuple[Flag, ...]
def oven_dry_mass_kg(weight_kg: float, basis: WeightBasis, absorption_pct: float, mc_pct: float) -> float
def ssd_mass_kg(oven_dry_kg: float, absorption_pct: float) -> float           # dry * (1 + Abs/100)
def free_water_kg(oven_dry_kg: float, mc_pct: float, absorption_pct: float) -> float  # dry * (MC - Abs)/100, sign kept
def aggregate_moisture(label: str, weight_kg: float, basis: WeightBasis, absorption_pct: float, mc_pct: float) -> AggregateMoisture
@dataclass(frozen=True) class WaterBreakdown: added_water_kg: float; free_water_ca_kg: float; free_water_fa_kg: float; effective_water_kg: float
def effective_water(added_water_kg: float, coarse: AggregateMoisture, fine: AggregateMoisture) -> WaterBreakdown
@dataclass(frozen=True) class FieldWeights:
    convention: MoistureConvention; coarse_wet_kg: float; fine_wet_kg: float; water_adjusted_kg: float
    coarse_free_water_kg: float; fine_free_water_kg: float
def field_weights_course(water_kg: float, coarse_dry_kg: float, fine_dry_kg: float, coarse_mc_pct: float, coarse_absorption_pct: float, fine_mc_pct: float, fine_absorption_pct: float) -> FieldWeights
def field_weights_strict(water_kg: float, coarse_ssd_kg: float, fine_ssd_kg: float, coarse_mc_pct: float, coarse_absorption_pct: float, fine_mc_pct: float, fine_absorption_pct: float) -> FieldWeights
```
Equations: task section 6 step 1 (dry by basis; ssd = dry(1+Abs/100); free = dry(MC-Abs)/100; COURSE wet = W(1+MC/100), adj = water - sum W(MC-Abs)/100; STRICT wet = SSD(1+MC/100)/(1+Abs/100), adj = water - sum SSD(MC-Abs)/(100+Abs)). basis = ssd -> effective MC := Abs, free water 0, flag if MC != Abs.
Tests: slide example in SI and lb/yd3 (cement 580, water 320, CA 1940 MC 2 Abs 1, FA 1110 MC 6 Abs 1.5): COURSE -> CA 1978.8, FA 1176.6, water 250.65 lb/yd3 (abs 1e-9 in lb/yd3; SI values = conversions, rel 1e-12); STRICT -> CA 1959.2079..., FA 1159.2118..., water 251.5803... (hand: 1940*1.02/1.01; 1110*1.06/1.015; 320 - 1940*1/101 - 1110*4.5/101.5); negative free water (MC 0.5 < Abs 2) kept negative + NEGATIVE_FREE_WATER flag; three bases on hypothesis-generated physical mixes -> same effective water (rel 1e-12) [oven_dry vs as_received any MC; ssd case only when MC == Abs, A-08]; mass balance: cement + added + wet aggregates == cement + effective water + SSD aggregates (rel 1e-12); strict field weights fed back as as_received -> oven-dry mass recovered exactly.

## M7 - volumes.py
Files: `volumes.py`, `tests/test_volumes.py`.
```python
def absolute_volume_m3(mass_kg: float, sg: float) -> float              # mass / (sg * 1000)
@dataclass(frozen=True) class VolumeCheck:
    cement_m3: float; scm_m3: float; water_m3: float; coarse_m3: float; fine_m3: float; air_m3: float
    total_m3: float; closure_error_m3: float; implied_air_pct: float; flags: tuple[Flag, ...]
def volume_check(binders: tuple[Binder, ...], effective_water_kg: float, coarse_ssd_kg: float, coarse_sg_ssd: float,
                 fine_ssd_kg: float, fine_sg_ssd: float, air_pct: float) -> VolumeCheck
@dataclass(frozen=True) class UnitWeightCheck:
    computed_kg_m3: float; aci_kg_m3: float | None; deviation_pct: float | None; status: Status; flags: tuple[Flag, ...]
def unit_weight_check(binders: tuple[Binder, ...], effective_water_kg: float, coarse_ssd_kg: float, fine_ssd_kg: float,
                      nmas_mm: float, air_entrained: bool, policy: Policy = "clamp") -> UnitWeightCheck
@dataclass(frozen=True) class PackingIndicators:
    coarse_void_content: float; coarse_bulk_ratio_actual: float; coarse_bulk_ratio_table: float | None
    coarse_bulk_ratio_deviation_pct: float | None; paste_volume_m3: float
    fine_fraction_by_mass: float; fine_fraction_by_volume: float; flags: tuple[Flag, ...]
def packing_indicators(coarse_dry_kg: float, coarse_ssd_kg: float, coarse: CoarseAggregateProperties, fine_ssd_kg: float,
                       fine: FineAggregateProperties, nmas_mm: float, volumes: VolumeCheck, policy: Policy = "extrapolate") -> PackingIndicators
```
Equations: V = W/(SG*1000); total = sum + air_pct/100; closure = total - 1; implied air % = (1 - (solids + water)) * 100; unit weight = binders + effective water + CA_ssd + FA_ssd; deviation % = 100(computed - ACI)/ACI; CA void content = 1 - DRD/(SG_OD*1000) with SG_OD = SG_ssd/(1+Abs/100) (A-09, Q22); actual b/b0 = CA_dry/DRD; deviation % vs table; paste = V_binders + V_water + V_air; FA fraction = FA_ssd/(FA_ssd+CA_ssd) by mass, V_FA/(V_FA+V_CA) by volume.
Flags (thresholds A-10): |closure| > 0.02 warning, > 0.05 error; unit-weight deviation > 5 %; |b/b0 deviation| > 10 %.
Tests: hand-computed volumes for a fixed mix (abs 1e-12); closure exactly at/just over each threshold; unit weight equals the mass sum; ACI comparison at node and off-node NMAS; indicators hand values; hypothesis: total - air == 1 - implied_air/100.

## M8 - required_strength.py
Files: `required_strength.py`, `tests/test_required_strength.py`.
```python
@dataclass(frozen=True) class RequiredStrength:
    fc_mpa: float; fcr_mpa: float; method: Literal["statistical", "no_data"]; f_factor: float | None
    sigma_mpa: float | None; candidate_134_mpa: float | None; candidate_233_mpa: float | None; governing: str; flags: tuple[Flag, ...]
def required_average_strength_mpa(fc_mpa: float, sigma_mpa: float | None, n_samples: int | None) -> RequiredStrength
@dataclass(frozen=True) class CharacteristicEstimate:
    fcr_mean_mpa: float; fc_est_mpa: float; margin_mpa: float; method: Literal["statistical", "no_data"]
    label: str; flags: tuple[Flag, ...]    # label = "estimated characteristic strength (research estimate)"
def estimated_characteristic_strength_mpa(fcr_mean_mpa: float, sigma_mpa: float | None, n_samples: int | None) -> CharacteristicEstimate
```
Equations: forward f'cr = max(f'c + 1.34 sF, f'c + 2.33 sF - 3.45); F from f_factor (n < 15 -> sigma treated unknown + flag; n None with sigma -> F = 1.00 + flag, A-11); no data: +7.0 (f'c < 21), +8.5 (21 <= f'c <= 35), +10.0 (f'c > 35). Inverse: f'c_est = f'cr - max(1.34 sF, 2.33 sF - 3.45); no data: candidates f'cr-7.0, f'cr-8.5, f'cr-10.0, keep those whose result lies in their own band; consistent bands are f'cr < 28, 29.5 <= f'cr <= 43.5, f'cr > 45 -> **two gaps**: [28, 29.5) and (43.5, 45]; in a gap take the lower (larger-margin) candidate of the two adjacent bands + flag (A-12).
Tests (abs 0.1 MPa vs slides, stated in test; abs 1e-9 vs hand calcs): f'c 31 no data -> 39.5; s 3.6 n 17 -> 37.01 (slide 37.1, discrepancy REPORTED in test docstring, not hidden); s 2.4 n >= 30 -> 34.22 (slide 34.3; abs 0.1 passes only just: |34.216-34.3| = 0.084); s 3.8 -> 36.40; F interpolation n 17 = 1.128; n 12 -> no-data branch + flag; band edges 20.99/21/35/35.01; inverse is the exact inverse of forward for every band and for sigma known (hypothesis); both gap regions -> lower candidate + flag.

## M9 - strength models + age + registry + model_constants.json
Files: `strength/__init__.py`, `strength/registry.py`, `strength/aci_table.py`, `strength/abrams.py`, `strength/bolomey.py`, `strength/feret.py`, `strength/age.py`, `calibration/__init__.py`, `calibration/fit.py` (numpy-only fit functions are needed here to produce/verify the default constants; dataset/store stay in M14 - A-13), `data/model_constants.json`, `tests/test_strength.py`.
```python
@dataclass(frozen=True) class MixState:
    cement_kg_m3: float; binder_kg_m3: float; effective_water_kg_m3: float; wc: float; wcm: float
    air_pct: float; air_entrained: bool; cement_volume_m3: float; water_volume_m3: float; air_volume_m3: float
    cement_type: CementType; curing: Curing; age_days: float
@dataclass(frozen=True) class ModelConstants:
    model_name: str; preset: str; values: dict[str, float]; source: str; calibrated: bool
    air_entrained: bool | None; age_basis_days: float; material_set_id: str | None = None
@dataclass(frozen=True) class StrengthPrediction:
    model_name: str; mean_28d_mpa: float | None; status: Status; warnings: tuple[str, ...]; flags: tuple[Flag, ...]
    constants_used: dict[str, float]; constants_source: str; calibrated: bool
StrengthModel = Callable[[MixState, ModelConstants], StrengthPrediction]
MODEL_REGISTRY: dict[str, StrengthModel]       # {"aci_table", "abrams", "bolomey", "feret"}
def default_constants(model_name: str, air_entrained: bool, preset: str = "project_fit") -> ModelConstants
def list_presets(model_name: str) -> tuple[str, ...]
def predict_aci_table(mix: MixState, constants: ModelConstants, policy: Policy = "extrapolate") -> StrengthPrediction
def predict_abrams(mix: MixState, constants: ModelConstants) -> StrengthPrediction     # f = A / B**wc
def predict_bolomey(mix: MixState, constants: ModelConstants) -> StrengthPrediction    # f = K (1/wc - 0.5)
def predict_feret(mix: MixState, constants: ModelConstants) -> StrengthPrediction      # f = K (Vc/(Vc+Vw+Va))**2
def strength_curve_mpa(model_name: str, wc_values: tuple[float, ...], reference: MixState, constants: ModelConstants) -> tuple[float | None, ...]
# calibration/fit.py
@dataclass(frozen=True) class FitResult: model_name: str; values: dict[str, float]; n_rows: int; r2: float; r2_space: str; r2_mpa: float; rmse_mpa: float
def fit_abrams(wc: np.ndarray, strength_mpa: np.ndarray) -> FitResult        # polyfit(wc, ln f, 1): slope = -ln B, intercept = ln A
def fit_bolomey(cw: np.ndarray, strength_mpa: np.ndarray) -> FitResult       # K = sum(f g)/sum(g g), g = C/W - 0.5
def fit_feret(volume_ratio: np.ndarray, strength_mpa: np.ndarray) -> FitResult  # g = (Vc/(Vc+Vw+Va))**2
# strength/age.py
@dataclass(frozen=True) class AgeAdjusted:
    f28_mpa: float; age_days: float; strength_mpa: float; factor: float; a_days: float; b: float
    normalised: bool; coefficient_type: CementType; flags: tuple[Flag, ...]
def age_factor(age_days: float, cement_type: CementType, curing: Curing, normalise_to_28d: bool = False) -> tuple[float, float, float, tuple[Flag, ...]]
def strength_at_age_mpa(f28_mpa: float, age_days: float, cement_type: CementType, curing: Curing, normalise_to_28d: bool = False) -> AgeAdjusted
```
Equations: age factor = t/(a+bt); normalised = [t/(a+bt)] / [28/(a+28b)]; Types II/IV/V -> Type I coefficients + flag; f28 outside 20-70 MPa -> flag. Feret volumes: Vc = C/(SGc*1000), Vw = W/1000, Va = air/100.
Provisional default constants (pre-computed from section 8 points; will be produced by `fit.py` and stored at full precision; a test re-fits from the JSON tables and compares to rel 1e-9):
- Abrams non-AE: A = 114.9086, B = 12.4972 (RMSE 0.95 MPa on 6 points); AE: A = 96.4816, B = 13.3792 (RMSE 0.62 MPa, 5 points).
- Bolomey non-AE: K = 20.5032 (RMSE 2.24); AE: K = 16.6538 (RMSE 1.68).
- Feret (one K for both columns): K = 230.00 (RMSE 1.74), fit points built with water = mixing-water table at NMAS 19 mm, slump 87.5 mm, angular (non-AE 205, AE 184), air 2.0 % non-AE / 5.0 % AE (moderate), cement SG 3.15, C = W/wc (A-14).
- Literature presets stored as unverified alternatives: abrams `lit_96_7` (A 96, B 7, 28 d), `lit_96.55_8.2` (28 d), `lit_63.45_14_7d` (7 d, `age_basis_days` 7; not used for 28-d prediction by default - D-4).
**Decision needed D-3:** `model_constants.json` needs a source string per preset, which the `mapping` kind cannot hold. Proposal: one extra kind `"presets"`: `{"meta": {...}, "kind": "presets", "presets": [{"model","preset","air_entrained","age_basis_days","values":{...},"source","verified": false}]}` with its own loader `load_presets()`. Fallback: mapping with keys "abrams.project_fit.non_ae.A" and sources listed in meta.notes.
**Decision needed D-4:** the 7-day Abrams preset: (a) store only, never used for 28-d output (recommended), or (b) convert with the age model f28 = f7 / factor(7).
Flags: w/c outside 0.25-0.85; w/c < 0.25 (full hydration 0.22-0.25); predicted strength outside 14-48 MPa; any CLAMPED/EXTRAPOLATED status; aci_table NMAS outside 19-25 mm (table basis, A-15); model spread (set in M11).
Tests: every model strictly decreasing in w/c (hypothesis over 0.25-0.85, both AE states); aci_table equals table at nodes; fitted defaults reproduce table points within RMSE-based tolerance (abs 2.5 MPa Abrams/Feret, 4.5 MPa Bolomey; stated); refit == stored constants; every prediction carries constants, source, calibrated False; registry keys; age: literal at 28 d within 1 % for moist I (1.0072), moist III (0.9979), steam III (0.9950) and **within 1.5 % for steam I (1.0145)** - the task's "within 1 %" fails for steam Type I (Q20); normalised exactly 1.0 (abs 1e-12) at 28 d; Type II -> Type I coefficients + flag; age monotonic increasing.

## M10 - slump.py
Files: `slump.py`, `tests/test_slump.py` (new test file; not in the allowed list of section 3 - A-16; alternative: put these tests in test_mode_b.py).
```python
@dataclass(frozen=True) class SlumpEstimate:
    slump_mm: float | None; status: Status; band_mm: float; lower_mm: float | None; upper_mm: float | None
    trial_tolerance_mm: float; flags: tuple[Flag, ...]
def estimate_slump_mm(effective_water_kg_m3: float, nmas_mm: float, air_entrained: bool, shape: AggregateShape,
                      element: ElementType | None = None, policy: Policy = "extrapolate") -> SlumpEstimate
def slump_delta_from_water_delta_mm(water_delta_kg_m3: float) -> float     # 25 * dw / 6
```
Equations: lookups.slump_for_water_mm; result < 0 -> 0 + flag; band +-25 mm (A-10), trial tolerance +-20 mm; outside the element's [min, max] -> flag; water reducer / superplasticizer present -> flag "estimate ignores admixtures".
Tests: water at each band midpoint returns 37.5/87.5/162.5 (abs 1e-9) for several NMAS and shapes; below/above water range EXTRAPOLATED; very low water -> clamped to 0 + flag; 150 mm NMAS uses only 2 rows; slide rule 6 kg/m3 -> 25 mm; element range flag.

## M11 - mode_b.py (Mode B end to end)
Files: `mode_b.py`, `tests/test_mode_b.py`.
```python
@dataclass(frozen=True) class StrengthPlotData:
    aci_non_ae_points: tuple[tuple[float, float], ...]; aci_ae_points: tuple[tuple[float, float], ...]
    model_curves: dict[str, tuple[tuple[float, float | None], ...]]   # w/c 0.25..0.85 step 0.01 (61 points, A-17)
    mix_point_wc: float; mix_point_strengths_mpa: dict[str, float | None]
@dataclass(frozen=True) class StrengthReport:
    inputs: MixInputs; per_m3_scale: float; cement_kg_m3: float; water_added_kg_m3: float; coarse_entered_kg_m3: float; fine_entered_kg_m3: float
    coarse: AggregateMoisture; fine: AggregateMoisture; water: WaterBreakdown; wc: float; wcm: float
    air_pct: float; air_source: Literal["aci_table", "user"]; volumes: VolumeCheck; unit_weight: UnitWeightCheck
    indicators: PackingIndicators; predictions: dict[str, StrengthPrediction]; age_adjusted: dict[str, AgeAdjusted | None]
    characteristic: dict[str, CharacteristicEstimate | None]; slump: SlumpEstimate; air_entrainer_dosage_ml_m3: float | None
    cube_equivalent_mpa: dict[str, float | None]; flags: tuple[Flag, ...]; plot: StrengthPlotData; disclaimer: str
def run_mode_b(inputs: MixInputs, constants: dict[str, ModelConstants] | None = None, policy: Policy = "extrapolate",
               normalise_age_to_28d: bool = False, model_spread_threshold_mpa: float = 5.0) -> StrengthReport
def report_to_dict(report: StrengthReport) -> dict                # JSON-safe (for export)
```
Steps: validate -> normalise per m3 (divide by batch volume) -> moisture -> effective water, w/c, w/cm -> air (table or user) -> volumes, unit weight, indicators -> MixState -> each registry model -> age adjustment -> characteristic estimate (if sigma) -> slump -> dosage 6.3 * air% * cement/100 ml/m3 (flag "slide value; product-specific") -> spread flag -> plot data. Cube: predictions are cylinder basis; with factor, cube equivalent = cylinder / factor (A-18, Q27); without factor -> flag, cylinder only.
Tests: integration on a hand-checked mix (all intermediate numbers asserted); batch normalisation (2 m3 batch == per-m3 input); basis invariance at report level; every prediction has DISCLAIMER/constants/calibrated; spread flag at threshold; plot data shapes; report_to_dict is json.dumps-able; SCM -> flag + w/cm computed; validation error propagates as ValueError.

## M12 - mix_design.py (Mode A)
Files: `mix_design.py`, `tests/test_mix_design.py`.
```python
@dataclass(frozen=True) class SlumpStep:  min_mm: float; max_mm: float; target_mm: float; flags: tuple[Flag, ...]
@dataclass(frozen=True) class NmasStep:   limits_mm: dict[str, float]; governing_limit: str | None; limit_mm: float | None; max_size_mm: float; nmas_mm: float; flags: tuple[Flag, ...]
@dataclass(frozen=True) class WaterAirStep: water_table_kg_m3: float; water_reduction_kg_m3: float; water_kg_m3: float; air_pct: float; flags: tuple[Flag, ...]
@dataclass(frozen=True) class WcStep:     fcr: RequiredStrength; wc_strength: float; wc_durability: float | None; wc: float; governing: Literal["strength", "durability"]; wc_specified_table: float | None; flags: tuple[Flag, ...]
@dataclass(frozen=True) class CementStep: cement_from_wc_kg_m3: float; minimum_kg_m3: float | None; minimum_reason: str | None; cement_kg_m3: float; wc_final: float; governing: Literal["strength", "durability", "min_cement"]; flags: tuple[Flag, ...]
@dataclass(frozen=True) class CoarseStep: bb0_table: float; bb0_used: float; coarse_dry_kg_m3: float; coarse_ssd_kg_m3: float; flags: tuple[Flag, ...]
@dataclass(frozen=True) class FineStep:   volumes_m3: dict[str, float]; fine_volume_m3: float; fine_ssd_kg_m3: float; unit_weight_kg_m3: float; fine_weight_method_kg_m3: float; method_difference_kg_m3: float; flags: tuple[Flag, ...]
@dataclass(frozen=True) class Proportions: cement: float; fine: float; coarse: float; water: float   # cement = 1
@dataclass(frozen=True) class BatchWeights: batch_volume_m3: float; cement_kg: float; water_kg: float; coarse_kg: float; fine_kg: float; trial_batch_guidance: tuple[str, ...]
@dataclass(frozen=True) class MixDesignReport:
    inputs: ModeAInputs; slump: SlumpStep; nmas: NmasStep; water_air: WaterAirStep; wc: WcStep; cement: CementStep
    coarse: CoarseStep; fine: FineStep; field: FieldWeights; field_other_convention: FieldWeights
    proportions: Proportions; batch: BatchWeights; governing_constraint: str; flags: tuple[Flag, ...]; disclaimer: str
def step1_slump(element: ElementType, slump_target_mm: float | None, hand_consolidated: bool) -> SlumpStep
def step2_nmas(form_min_dimension_mm: float | None, rebar_clear_spacing_mm: float | None, cover_mm: float | None, slab_thickness_mm: float | None, nmas_override_mm: float | None) -> NmasStep
def step3_water_air(slump_mm: float, nmas_mm: float, air_entrained: bool, exposure: Exposure, shape: AggregateShape, water_reducer_pct: float | None) -> WaterAirStep
def step4_wc(specified_fc_mpa: float, sigma_mpa: float | None, n_samples: int | None, air_entrained: bool, durability_class: DurabilityClass) -> WcStep
def step5_cement(water_kg_m3: float, wc: float, wc_governing: str, nmas_mm: float, exposure: Exposure, underwater: bool, flatwork: bool) -> CementStep
def step6_coarse(nmas_mm: float, fm: float, drd_kg_m3: float, absorption_pct: float, adjustment_factor: float) -> CoarseStep
def step7_fine(cement_kg_m3: float, cement_sg: float, water_kg_m3: float, air_pct: float, coarse_ssd_kg_m3: float, coarse_sg_ssd: float, fine_sg_ssd: float, nmas_mm: float, air_entrained: bool) -> FineStep
def step8_moisture(convention: MoistureConvention, water_kg_m3: float, coarse: CoarseStep, fine: FineStep, coarse_props: CoarseAggregateProperties, fine_props: FineAggregateProperties) -> FieldWeights
def step9_proportions(cement_kg_m3: float, field: FieldWeights) -> Proportions
def step10_batch(cement_kg_m3: float, field: FieldWeights, batch_volume_m3: float) -> BatchWeights
def design_mix(inputs: ModeAInputs, policy: Policy = "extrapolate") -> MixDesignReport
def to_mode_b_inputs(design: MixDesignReport) -> MixInputs   # as_received basis, field (wet) weights, adjusted water, design air
```
Equations: task section 7. NMAS: limits 1/5 form, 3/4 min(spacing, cover) of those given, 1/3 slab; max_size = largest sieve <= limit; NMAS = next smaller sieve; max_size = 9.5 -> NMAS 9.5 + flag; limit < 9.5 -> error-level flag. Water reducer: water *= (1 - pct/100) (A-19). Step 4 governing = min(w/c). Step 5 min cement = max of applicable (severe exposure 334, underwater 385, flatwork table); if cement < min: cement = min, w/c = water/cement. Step 7 volume method on SSD basis; weight method FA = U - (water + cement + CA_ssd). Step 8: course convention uses CA_dry and FA_ssd as "design weights" exactly as the slides do; strict uses CA_ssd and FA_ssd (A-20). Both conventions are always computed; the selected one is `field`, the other is `field_other_convention`.
Tests: NMAS example 200 mm form, 40 mm spacing/cover -> limit 30 -> max 25 -> NMAS 19; each step against hand values; governing w/c cases (strength vs durability vs min cement); volume sum == 1 m3 (abs 1e-12) for designs (hypothesis); proportions slide check 1 : 2.03 : 3.41 : 0.43 from the moisture example weights; round trip: design -> to_mode_b_inputs -> run_mode_b -> effective water == design water (rel 1e-9, both conventions for water; strict also recovers masses exactly) and aci_table mean within 0.5 MPa of f'cr when strength governs; when durability/min cement governs the report names the constraint and the test asserts the predicted mean > f'cr; Abrams/Bolomey/Feret round-trip discrepancies asserted within abs 4.5 MPa and reported.

## M13 - docs/hand_calcs.md + tests/test_examples.py
Files: `docs/hand_calcs.md` (written FIRST, by hand arithmetic, before running the code on the examples), `tests/test_examples.py`.
Example 1 (3000 psi = 20.684 MPa; moderate exposure foundation; NMAS 37.5 mm; CA SG 2.69, Abs 0.8, MC 2, DRD 105 pcf = 1681.94 kg/m3; FA SG 2.65, Abs 6, MC 8, FM 2.6). Unstated inputs, computed in BOTH variants where cheap: air entrainment (non-AE and AE moderate), element (reinforced foundation walls/footings -> slump 25-75 mm), shape (angular), sigma (unknown -> +7.0 because 20.68 < 21; also shown with +8.5 for the 21 MPa reading, Q7).
Example 2 (24.1 MPa; sigma 2.4, n > 30; 25 mm round river gravel; CA SG 2.62, Abs 0.4, MC 1.5, DRD 1681; FA SG 2.57, Abs 0.8, MC 4, FM 2.6; AE; bridge pier, freeze-thaw). Unstated: element (bridge pier -> beams/reinforced walls? or columns? both give 25-100 mm), exposure (severe vs moderate, both), durability class freeze_thaw_moist (w/c 0.45; min f'c 31.03 MPa > 24.1 -> flag), whether "25 mm" is max size or NMAS (both).
Tests assert code == hand calc (abs 0.01 kg/m3 / 0.001 w/c / 0.01 MPa, stated); hand calc is never edited to match the code - any mismatch is reported.

## M14 - calibration (fit, store, dataset) + CSV template + experiment log layout
Files: `calibration/fit.py` (extend: `fit_all`, age policy), `calibration/store.py`, `calibration/dataset.py`, `experiments/mix_log_template.csv`, `docs/experiment_log_layout.md`, `calibrations/.gitkeep`, `tests/test_calibration.py`.
```python
@dataclass(frozen=True) class CalibrationRow: ...                      # one field per schema column (task section 10), SI
def load_rows(path: str | Path) -> tuple[tuple[CalibrationRow, ...], tuple[tuple[int, str, str], ...]]   # pandas; (row_number, column, message)
def rows_to_fit_arrays(rows: tuple[CalibrationRow, ...], age_policy: Literal["only_28d", "convert"] = "only_28d") -> FitArrays   # uses mode_b steps for effective w/c and volumes
def fit_all(arrays: FitArrays) -> dict[str, FitResult]                  # >= 3 rows else ValueError
def comparison_table(results: dict[str, FitResult]) -> tuple[tuple[str, int, float, float, float], ...]
def save_calibration(material_set_id: str, model_name: str, result: FitResult, source_csv: str, data_hash: str, directory: Path = Path("calibrations")) -> Path
def load_calibration(material_set_id: str, model_name: str, directory: Path = Path("calibrations")) -> ModelConstants   # calibrated=True
def file_sha256(path: str | Path) -> str
```
Store JSON: {material_set_id, model, constants, fit_stats, n_rows, source_csv, data_hash, created_utc} (one file per material set holding all fitted models). `created_utc` is passed in / taken at the boundary so the fit stays pure (A-21). Cube rows: converted with the user's factor only if a factor column exists; otherwise rejected with an error row (Q4).
Tests: synthetic data from A = 100, B = 10 with 3 % multiplicative noise (seeded numpy Generator) -> A, B recovered within rel 10 %, R2 (log) > 0.95; Bolomey/Feret recover K within rel 5 %; < 3 rows -> ValueError; non-28-d rows excluded by default and converted with "convert"; dataset: every bad cell reported with row number, not aborting; reserved columns accepted and ignored; store round trip; calibrated flag True only from store.

## M15 - Streamlit UI (3 commits: Mode B page, Mode A page, Calibration page)
Files: `app/streamlit_app.py`, `app/adapters.py`, `tests/test_adapters.py` (+ AppTest smoke test, skipped if streamlit is not installed, A-22).
```python
# app/adapters.py (pure; imports concretecalc + units only)
UnitSystem = Literal["SI", "US"]
def mode_b_inputs_from_widgets(values: dict[str, object], unit_system: UnitSystem) -> MixInputs
def mode_a_inputs_from_widgets(values: dict[str, object], unit_system: UnitSystem) -> ModeAInputs
def report_rows_for_display(report: StrengthReport, unit_system: UnitSystem) -> dict[str, list[tuple[str, str]]]
def report_to_csv_text(report: StrengthReport) -> str
def default_air_pct(nmas_mm: float, exposure: Exposure, air_entrained: bool) -> float
```
UI per task section 11: st.number_input only (no sliders), bordered containers per material, prominent basis selector with help text, session_state air override, flags via st.error/st.warning/st.info, matplotlib plot, JSON/CSV download, permanent DISCLAIMER banner, Mode A collapsible 10-step walkthrough + "Predict this design back in Mode B", calibration upload/fit/save/select.
Tests: adapters SI and US (US inputs converted exactly; round trip); defaults produce a valid MixInputs; AppTest: app runs with defaults, no exception.

## M16 - Hardening
Files: `README.md`, final `OPEN_QUESTIONS.md`/`ASSUMPTIONS.md`, docs touch-ups.
README: PowerShell setup/run (`streamlit run app/streamlit_app.py`), text architecture diagram, "how to add a model (incl. a future ML model) to the registry", where the data tables live and how to mark them verified.
**Decision needed D-5:** "coverage summary" needs `pytest-cov` (not in the allowed dependency list). Options: add `pytest-cov` to `dev` extra, or report a manual per-module test inventory instead.

---

## Summary of decisions (ALL APPROVED by the owner 2026-11-01, as recommended)
- D-1 two extra JSON files for numeric rules/thresholds (or module constants).
- D-2 slump lookup for Mode A: midpoint interpolation (spec) vs band reading (recommended option b).
- D-3 `presets` JSON kind for model_constants.json (or mapping + notes).
- D-4 7-day Abrams preset: store only (recommended) or age-convert.
- D-5 pytest-cov for M16 coverage.
- D-6 `tests/test_slump.py` as an extra test file (A-16); `calibration/fit.py` created early in M9 (A-13).
