"""Domain-named table lookups: the ONLY way engine code reads reference tables.

Each function names its inputs with units, picks the right table/column, and
delegates the arithmetic to interp1d / interp2d (tables/interpolate.py). Every
numeric lookup returns a Lookup(value, status, warnings) so callers can turn
CLAMPED / EXTRAPOLATED / UNAVAILABLE into flags.

Sources of all numbers: src/concretecalc/data/*.json (see each file's meta.source).
"""

import math

import numpy as np

from concretecalc.schemas import (
    AGGREGATE_SHAPES,
    DURABILITY_CLASSES,
    ELEMENT_TYPES,
    EXPOSURES,
    SLUMP_LOOKUPS,
    AggregateShape,
    DurabilityClass,
    ElementType,
    Exposure,
    SlumpLookup,
)
from concretecalc.tables.interpolate import OutOfRangeError, Policy, interp1d, interp2d
from concretecalc.tables.loader import load_grid, load_mapping, load_series
from concretecalc.tables.models import Lookup, Status, worst
from concretecalc.units import psi_to_mpa


def input_validation_limits() -> dict[str, float]:
    """Return independent input-limit data for validation (PLAN M5).

    Table-axis bounds are read from the source table rather than duplicated.
    """
    limits = dict(load_mapping('flag_thresholds').values)
    grid = load_grid('bulk_volume_ca')
    limits['fm.table_min'] = float(grid.cols[0])
    limits['fm.table_max'] = float(grid.cols[-1])
    return limits


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _require_choice(value: str, allowed: tuple[str, ...], name: str) -> None:
    """Raise ValueError if value is not one of the allowed labels (Literal types are not checked at runtime)."""
    if value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")


def _ae_column(air_entrained: bool) -> str:
    """Column name used by the tables that have a non-AE and an AE variant."""
    if air_entrained:
        return "ae"
    return "non_ae"


def _unique(messages: list[str]) -> tuple[str, ...]:
    """Drop repeated warning texts, keeping their first-seen order."""
    result: list[str] = []
    for message in messages:
        if message not in result:
            result.append(message)
    return tuple(result)


def _ok(value: float) -> Lookup:
    return Lookup(value=float(value), status=Status.OK)


# ---------------------------------------------------------------------------
# w/c vs strength (wc_vs_strength.json, wc_vs_specified_fc.json)
# ---------------------------------------------------------------------------

def wc_for_strength(fcr_mpa: float, air_entrained: bool, policy: Policy = "extrapolate") -> Lookup:
    """w/c (-) for a required AVERAGE 28-day strength f'cr (MPa), moist cured, 19-25 mm aggregate.

    Linear interpolation in table wc_vs_strength (CIE308 slides after ACI 211.1).
    The AE column has no value at 48 MPa; that point is dropped, so AE queries above
    41 MPa are EXTRAPOLATED.
    """
    table = load_series("wc_vs_strength")
    column = table.columns[_ae_column(air_entrained)]
    return interp1d(fcr_mpa, table.x, column, policy, "fcr_mpa")


def strength_for_wc(wc: float, air_entrained: bool, policy: Policy = "extrapolate") -> Lookup:
    """Mean 28-day strength f'cr (MPa) for a w/c: the inverse of wc_for_strength (same table).

    The table's f'cr is a required AVERAGE strength, i.e. a mean, which is why it
    can be used for prediction.
    """
    table = load_series("wc_vs_strength")
    column = table.columns[_ae_column(air_entrained)]
    # Swap axes: the w/c column becomes the interpolation axis (interp1d sorts it).
    return interp1d(wc, column, table.x, policy, "wc")


def wc_for_specified_fc(fc_mpa: float, air_entrained: bool, policy: Policy = "extrapolate") -> Lookup:
    """w/c (-) from the SPECIFIED-strength table (stored, not the default basis; OPEN_QUESTIONS Q2)."""
    table = load_series("wc_vs_specified_fc")
    column = table.columns[_ae_column(air_entrained)]
    return interp1d(fc_mpa, table.x, column, policy, "fc_mpa")


def strength_table_range_mpa() -> tuple[float, float]:
    """(lowest, highest) f'cr in wc_vs_strength, MPa. Read from the table so it never drifts from the data."""
    table = load_series("wc_vs_strength")
    return float(table.x[0]), float(table.x[-1])


# ---------------------------------------------------------------------------
# Mixing water and slump (mixing_water.json, mixing_water_slump_bands.json, shape_reduction.json)
# ---------------------------------------------------------------------------

def shape_reduction_kg_m3(shape: AggregateShape) -> Lookup:
    """Mixing-water reduction (kg/m3) to subtract from the angular-aggregate table value."""
    _require_choice(shape, AGGREGATE_SHAPES, "shape")
    values = load_mapping("shape_reduction").values
    return _ok(values[shape])


def _slump_bands_mm() -> list[tuple[float, float]]:
    """[(min, max), ...] for the low, mid and high slump bands, in row order of mixing_water."""
    values = load_mapping("mixing_water_slump_bands").values
    bands = []
    for name in ("band_low", "band_mid", "band_high"):
        bands.append((values[f"{name}.min_mm"], values[f"{name}.max_mm"]))
    return bands


def _band_label(band: tuple[float, float]) -> str:
    return f"{band[0]:g}-{band[1]:g} mm"


def _water_at_row(row_index: int, nmas_mm: float, air_entrained: bool, policy: Policy) -> Lookup:
    """Angular-aggregate water (kg/m3) on one slump row of the table, interpolated over NMAS.

    Uses interp2d exactly on the row's midpoint, so the other rows get zero weight and a
    null cell is reported as UNAVAILABLE in the same way as in a normal 2-D lookup.
    """
    table = load_grid("mixing_water")
    grid = table.variants[_ae_column(air_entrained)]
    row_mm = float(table.rows[row_index])
    return interp2d(row_mm, nmas_mm, table.rows, table.cols, grid, policy, "slump_mm", "nmas_mm")


def _band_water_kg_m3(slump_mm: float, nmas_mm: float, air_entrained: bool, policy: Policy) -> Lookup:
    """Band reading of the mixing-water table (D-2), before the shape reduction.

    - slump inside a band (edges included) -> that band's row
    - slump between two bands               -> linear between the upper edge of the lower band
                                               and the lower edge of the upper band
    - slump outside all bands               -> "raise": OutOfRangeError; otherwise the end row,
                                               status CLAMPED (a band is never extrapolated; A-41)
    """
    if policy not in ("clamp", "extrapolate", "raise"):
        raise ValueError(f"unknown out-of-range policy {policy!r}")
    if math.isnan(slump_mm):
        raise ValueError("slump_mm is NaN; a table cannot be queried with NaN")

    bands = _slump_bands_mm()
    lowest = bands[0][0]
    highest = bands[-1][1]

    if slump_mm < lowest or slump_mm > highest:
        message = f"slump_mm={slump_mm:g} outside the slump bands [{lowest:g}, {highest:g}]"
        if policy == "raise":
            raise OutOfRangeError(message)
        if slump_mm < lowest:
            end_row = 0
        else:
            end_row = len(bands) - 1
        row_lookup = _water_at_row(end_row, nmas_mm, air_entrained, policy)
        if row_lookup.value is None:
            return row_lookup
        note = f"{message} (band {_band_label(bands[end_row])} used; band reading does not extrapolate)"
        return Lookup(
            value=row_lookup.value,
            status=worst(row_lookup.status, Status.CLAMPED),
            warnings=row_lookup.warnings + (note,),
        )

    for row_index in range(len(bands)):
        band_min, band_max = bands[row_index]
        if band_min <= slump_mm <= band_max:
            return _water_at_row(row_index, nmas_mm, air_entrained, policy)

    # Not inside a band, so it lies in a gap between two consecutive bands.
    for row_index in range(len(bands) - 1):
        gap_start = bands[row_index][1]
        gap_end = bands[row_index + 1][0]
        if gap_start < slump_mm < gap_end:
            lower = _water_at_row(row_index, nmas_mm, air_entrained, policy)
            if lower.value is None:
                return lower
            upper = _water_at_row(row_index + 1, nmas_mm, air_entrained, policy)
            if upper.value is None:
                return upper
            between = interp1d(
                slump_mm,
                np.array([gap_start, gap_end]),
                np.array([lower.value, upper.value]),
                "raise",
                "slump_mm",
            )
            return Lookup(
                value=between.value,
                status=worst(lower.status, upper.status),
                warnings=_unique(list(lower.warnings) + list(upper.warnings)),
            )

    # Only reachable if the band table itself were malformed (overlapping bands).
    raise ValueError(f"slump_mm={slump_mm:g} could not be placed in the slump bands {bands}")


def mixing_water_kg_m3(
    slump_mm: float,
    nmas_mm: float,
    air_entrained: bool,
    shape: AggregateShape,
    policy: Policy = "clamp",
    slump_lookup: SlumpLookup = "interpolate",
) -> Lookup:
    """Approximate mixing water (kg/m3) for a target slump, NMAS, air entrainment and aggregate shape.

    water = table(slump, NMAS) - shape_reduction(shape)
    slump_lookup = "interpolate": bilinear over (slump band midpoints 37.5/87.5/162.5 mm, NMAS) [task default]
    slump_lookup = "band"       : band reading along slump, linear over NMAS (D-2; see _band_water_kg_m3)
    Source: mixing_water.json, shape_reduction.json (CIE308 slides after ACI 211.1).
    """
    _require_choice(shape, AGGREGATE_SHAPES, "shape")
    _require_choice(slump_lookup, SLUMP_LOOKUPS, "slump_lookup")
    reduction_kg_m3 = shape_reduction_kg_m3(shape).value

    if slump_lookup == "interpolate":
        table = load_grid("mixing_water")
        grid = table.variants[_ae_column(air_entrained)]
        angular = interp2d(slump_mm, nmas_mm, table.rows, table.cols, grid, policy, "slump_mm", "nmas_mm")
    else:
        angular = _band_water_kg_m3(slump_mm, nmas_mm, air_entrained, policy)

    if angular.value is None:
        return angular
    return Lookup(value=angular.value - reduction_kg_m3, status=angular.status, warnings=angular.warnings)


def slump_for_water_mm(
    water_kg_m3: float,
    nmas_mm: float,
    air_entrained: bool,
    shape: AggregateShape,
    policy: Policy = "extrapolate",
) -> Lookup:
    """Slump (mm) that the mixing-water table associates with a water content: the table inverted.

    For the given NMAS and shape, build the water at each slump-band midpoint
    (37.5 / 87.5 / 162.5 mm), skipping bands with no data, subtract the shape
    reduction, then interpolate slump as a function of water. This is an ESTIMATE
    used by slump.py (M10); the policy applies to both the NMAS and the water axis.
    """
    _require_choice(shape, AGGREGATE_SHAPES, "shape")
    reduction_kg_m3 = shape_reduction_kg_m3(shape).value
    table = load_grid("mixing_water")
    bands = _slump_bands_mm()

    waters: list[float] = []
    slumps: list[float] = []
    statuses: list[Status] = []
    messages: list[str] = []
    for row_index in range(table.rows.size):
        row_lookup = _water_at_row(row_index, nmas_mm, air_entrained, policy)
        if row_lookup.value is None:
            messages.append(
                f"slump band {_band_label(bands[row_index])} has no mixing-water data at "
                f"nmas_mm={nmas_mm:g}; slump estimated from the remaining bands"
            )
            continue
        waters.append(row_lookup.value - reduction_kg_m3)
        slumps.append(float(table.rows[row_index]))
        statuses.append(row_lookup.status)
        messages.extend(row_lookup.warnings)

    inverse = interp1d(water_kg_m3, np.array(waters), np.array(slumps), policy, "water_kg_m3")
    messages.extend(inverse.warnings)
    return Lookup(value=inverse.value, status=worst(inverse.status, *statuses), warnings=_unique(messages))


# ---------------------------------------------------------------------------
# Air, coarse aggregate volume, unit weight
# ---------------------------------------------------------------------------

def air_content_pct(nmas_mm: float, exposure: Exposure | None, air_entrained: bool, policy: Policy = "clamp") -> Lookup:
    """Approximate air content (%, plain number) by NMAS.

    Non-AE: entrapped air column (exposure ignored). AE: column for the exposure
    (mild / moderate / severe), which is then required. Source: air_content.json.
    """
    if exposure is not None:
        _require_choice(exposure, EXPOSURES, "exposure")
    if air_entrained:
        if exposure is None:
            raise ValueError("exposure is required to look up the air content of air-entrained concrete")
        column_name = f"ae_{exposure}"
    else:
        column_name = "non_ae"
    table = load_series("air_content")
    return interp1d(nmas_mm, table.x, table.columns[column_name], policy, "nmas_mm")


def bulk_volume_ratio(nmas_mm: float, fm: float, policy: Policy = "extrapolate") -> Lookup:
    """b/b0: dry-rodded coarse-aggregate volume per unit volume of concrete (-), bilinear over (NMAS, FM).

    FM outside 2.40-3.00 is extrapolated by default (task section 5). Source: bulk_volume_ca.json.
    """
    table = load_grid("bulk_volume_ca")
    return interp2d(nmas_mm, fm, table.rows, table.cols, table.variants["b_b0"], policy, "nmas_mm", "fm")


def fm_table_range() -> tuple[float, float]:
    """(lowest, highest) fineness modulus covered by the b/b0 table."""
    table = load_grid("bulk_volume_ca")
    return float(table.cols[0]), float(table.cols[-1])


def fresh_unit_weight_kg_m3(nmas_mm: float, air_entrained: bool, policy: Policy = "clamp") -> Lookup:
    """First estimate of fresh concrete unit weight (kg/m3) by NMAS. Source: unit_weight.json."""
    table = load_series("unit_weight")
    return interp1d(nmas_mm, table.x, table.columns[_ae_column(air_entrained)], policy, "nmas_mm")


# ---------------------------------------------------------------------------
# Slump ranges (slump_ranges.json)
# ---------------------------------------------------------------------------

def slump_limits_mm(element: ElementType) -> tuple[Lookup, Lookup]:
    """(minimum, maximum) recommended slump in mm for a type of construction."""
    _require_choice(element, ELEMENT_TYPES, "element")
    values = load_mapping("slump_ranges").values
    return _ok(values[f"{element}.min_mm"]), _ok(values[f"{element}.max_mm"])


def hand_consolidation_extra_mm() -> Lookup:
    """Allowed increase of the maximum slump (mm) when concrete is consolidated by hand."""
    values = load_mapping("slump_ranges").values
    return _ok(values["mass_concrete.hand_consolidation_extra_mm"])


# ---------------------------------------------------------------------------
# Statistics and durability
# ---------------------------------------------------------------------------

def f_factor(n_samples: int) -> Lookup:
    """Modification factor F (-) for the standard deviation, by number of test results n.

    Linear between listed n (15, 20, 25, 30); F = 1.00 for n >= 30 (status OK, it is the
    rule, not a clamp); n < 15 -> UNAVAILABLE: the standard deviation is treated as unknown.
    Source: f_factor.json, required_strength_rules.json.
    """
    if n_samples < 0:
        raise ValueError(f"n_samples must be >= 0, got {n_samples}")
    min_n = load_mapping("required_strength_rules").values["f_factor.min_n"]
    if n_samples < min_n:
        message = f"n_samples={n_samples} < {min_n:g}: standard deviation treated as unknown"
        return Lookup(value=None, status=Status.UNAVAILABLE, warnings=(message,))
    table = load_series("f_factor")
    if n_samples >= table.x[-1]:
        return _ok(table.columns["f"][-1])
    return interp1d(float(n_samples), table.x, table.columns["f"], "raise", "n_samples")


def max_wc_durability(durability_class: DurabilityClass) -> Lookup:
    """Maximum w/c (-) for a durability exposure class. Class "none" -> Lookup(None, OK): no limit."""
    _require_choice(durability_class, DURABILITY_CLASSES, "durability_class")
    if durability_class == "none":
        return Lookup(value=None, status=Status.OK)
    return _ok(load_mapping("durability").values[f"{durability_class}.max_wc"])


def min_fc_durability_mpa(durability_class: DurabilityClass) -> Lookup:
    """Minimum f'c (MPa) for a durability class; stored in psi, converted with units.psi_to_mpa."""
    _require_choice(durability_class, DURABILITY_CLASSES, "durability_class")
    if durability_class == "none":
        return Lookup(value=None, status=Status.OK)
    psi = load_mapping("durability").values[f"{durability_class}.min_fc_psi"]
    return _ok(psi_to_mpa(psi))


def full_hydration_wc_limits() -> tuple[Lookup, Lookup]:
    """(lower, upper) of the full-hydration minimum w/c range, 0.22-0.25 (-)."""
    values = load_mapping("durability").values
    return _ok(values["full_hydration.min_wc_lower"]), _ok(values["full_hydration.min_wc_upper"])


# ---------------------------------------------------------------------------
# Minimum cement contents
# ---------------------------------------------------------------------------

def min_cement_flatwork_kg_m3(nmas_mm: float) -> Lookup:
    """ACI 302 minimum cement (kg/m3) for flatwork by NMAS.

    Linear between listed NMAS; below 9.5 mm clamped; above 37.5 mm the table has no
    value -> UNAVAILABLE (ASSUMPTIONS A-05, OPEN_QUESTIONS Q19).
    """
    table = load_series("min_cement_flatwork")
    largest = float(table.x[-1])
    if nmas_mm > largest:
        message = f"nmas_mm={nmas_mm:g}: no flatwork minimum cement listed above {largest:g} mm"
        return Lookup(value=None, status=Status.UNAVAILABLE, warnings=(message,))
    return interp1d(nmas_mm, table.x, table.columns["min_cement_kg_m3"], "clamp", "nmas_mm")


def min_cement_misc_kg_m3(condition: str) -> Lookup:
    """Other minimum cement contents (kg/m3): "severe_exposure" or "underwater"."""
    values = load_mapping("min_cement_misc").values
    _require_choice(condition, tuple(values), "condition")
    return _ok(values[condition])


# ---------------------------------------------------------------------------
# Sieves, rules, thresholds
# ---------------------------------------------------------------------------

def standard_sieves_mm() -> tuple[float, ...]:
    """The standard sieve sizes (mm), ascending."""
    return tuple(sorted(load_mapping("standard_sieves").values.values()))


def is_standard_nmas(nmas_mm: float) -> bool:
    """True if nmas_mm equals one of the standard sieve sizes (within 1e-9 mm)."""
    for size_mm in standard_sieves_mm():
        if abs(nmas_mm - size_mm) < 1e-9:
            return True
    return False


def threshold(key: str) -> float:
    """A value from flag_thresholds.json (placeholders, slide rules, input limits). KeyError if unknown."""
    values = load_mapping("flag_thresholds").values
    if key not in values:
        raise KeyError(f"no threshold named {key!r} in flag_thresholds.json")
    return values[key]


def required_strength_rule(key: str) -> float:
    """A value from required_strength_rules.json (1.34, 2.33, 3.45, margins, band edges). KeyError if unknown."""
    values = load_mapping("required_strength_rules").values
    if key not in values:
        raise KeyError(f"no rule named {key!r} in required_strength_rules.json")
    return values[key]
