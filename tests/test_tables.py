"""Tests for the table layer (tables/).

M1 section: tables/models.py - Status, worst(), Lookup, TableMeta and the
three table containers (Series1D, Grid2D, LabelMap) with load-time validation.
Later milestones (M2 interpolate, M3 loader, M4 lookups) append their own sections.
"""

import dataclasses

import numpy as np
import pytest

from concretecalc.tables.models import (
    Grid2D,
    LabelMap,
    Lookup,
    Series1D,
    Status,
    TableMeta,
    worst,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_meta(table_id: str = "test_table") -> TableMeta:
    """A minimal valid TableMeta used by every container test."""
    return TableMeta(
        id=table_id,
        title="Test table",
        source="unit test",
        verified_against_primary=False,
        units={"x": "mm", "y": "kg/m3"},
        notes="",
    )


def make_series(x, columns) -> Series1D:
    return Series1D(
        meta=make_meta(),
        x=np.array(x, dtype=float),
        columns={name: np.array(values, dtype=float) for name, values in columns.items()},
    )


def make_grid(rows, cols, variants) -> Grid2D:
    return Grid2D(
        meta=make_meta(),
        rows=np.array(rows, dtype=float),
        cols=np.array(cols, dtype=float),
        variants={name: np.array(values, dtype=float) for name, values in variants.items()},
    )


# ---------------------------------------------------------------------------
# Status and worst()
# ---------------------------------------------------------------------------

SEVERITY_ORDER = [Status.OK, Status.CLAMPED, Status.EXTRAPOLATED, Status.UNAVAILABLE]


def test_status_values_are_lowercase_strings():
    # A-38: lowercase values; Status is a str Enum so it serialises to JSON directly.
    assert Status.OK == "ok"
    assert Status.CLAMPED == "clamped"
    assert Status.EXTRAPOLATED == "extrapolated"
    assert Status.UNAVAILABLE == "unavailable"


def test_worst_of_nothing_is_ok():
    # A-01
    assert worst() is Status.OK


def test_worst_of_single_status_is_itself():
    for status in SEVERITY_ORDER:
        assert worst(status) is status


@pytest.mark.parametrize("i", range(4))
@pytest.mark.parametrize("j", range(4))
def test_worst_of_every_pair_follows_severity_order(i, j):
    expected = SEVERITY_ORDER[max(i, j)]
    assert worst(SEVERITY_ORDER[i], SEVERITY_ORDER[j]) is expected


def test_worst_of_many():
    assert worst(Status.OK, Status.EXTRAPOLATED, Status.CLAMPED, Status.OK) is Status.EXTRAPOLATED


def test_worst_rejects_non_status():
    with pytest.raises(TypeError):
        worst(Status.OK, "ok")


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

def test_lookup_defaults_to_no_warnings():
    lookup = Lookup(value=205.0, status=Status.OK)
    assert lookup.value == 205.0
    assert lookup.status is Status.OK
    assert lookup.warnings == ()


def test_lookup_can_hold_no_value():
    lookup = Lookup(value=None, status=Status.UNAVAILABLE, warnings=("null cell",))
    assert lookup.value is None
    assert lookup.warnings == ("null cell",)


def test_lookup_is_frozen():
    lookup = Lookup(value=1.0, status=Status.OK)
    with pytest.raises(dataclasses.FrozenInstanceError):
        lookup.value = 2.0


# ---------------------------------------------------------------------------
# TableMeta
# ---------------------------------------------------------------------------

def test_table_meta_fields_match_json_meta():
    names = [field.name for field in dataclasses.fields(TableMeta)]
    assert names == ["id", "title", "source", "verified_against_primary", "units", "notes"]


def test_table_meta_is_frozen():
    meta = make_meta()
    with pytest.raises(dataclasses.FrozenInstanceError):
        meta.source = "memory"


# ---------------------------------------------------------------------------
# Series1D
# ---------------------------------------------------------------------------

def test_valid_series_constructs():
    table = make_series([14, 21, 28], {"non_ae": [0.82, 0.68, 0.57], "ae": [0.74, 0.59, np.nan]})
    assert table.x.shape == (3,)
    assert set(table.columns) == {"non_ae", "ae"}


def test_series_allows_nan_in_column_values():
    # JSON null = "no data" -> NaN; only axes must be NaN-free.
    table = make_series([1, 2], {"a": [np.nan, 1.0]})
    assert np.isnan(table.columns["a"][0])


def test_series_rejects_2d_axis():
    with pytest.raises(ValueError, match="test_table"):
        Series1D(meta=make_meta(), x=np.array([[1.0, 2.0]]), columns={"a": np.array([1.0, 2.0])})


def test_series_rejects_single_point_axis():
    with pytest.raises(ValueError):
        make_series([1], {"a": [1]})


def test_series_rejects_repeated_axis_values():
    with pytest.raises(ValueError):
        make_series([1, 2, 2], {"a": [1, 2, 3]})


def test_series_rejects_decreasing_axis():
    with pytest.raises(ValueError):
        make_series([3, 2, 1], {"a": [1, 2, 3]})


def test_series_rejects_nan_in_axis():
    with pytest.raises(ValueError):
        make_series([1, np.nan, 3], {"a": [1, 2, 3]})


def test_series_rejects_wrong_column_length():
    with pytest.raises(ValueError, match="short"):
        make_series([1, 2, 3], {"short": [1, 2]})


def test_series_rejects_no_columns():
    with pytest.raises(ValueError):
        make_series([1, 2], {})


# ---------------------------------------------------------------------------
# Grid2D
# ---------------------------------------------------------------------------

def test_valid_grid_constructs():
    table = make_grid(
        rows=[37.5, 87.5, 162.5],
        cols=[9.5, 12.5],
        variants={"non_ae": [[207, 199], [228, 216], [243, 228]]},
    )
    assert table.variants["non_ae"].shape == (3, 2)


def test_grid_allows_nan_cells():
    table = make_grid([1, 2], [1, 2], {"v": [[1, 2], [3, np.nan]]})
    assert np.isnan(table.variants["v"][1, 1])


def test_grid_rejects_bad_row_axis():
    with pytest.raises(ValueError):
        make_grid([2, 1], [1, 2], {"v": [[1, 2], [3, 4]]})


def test_grid_rejects_bad_col_axis():
    with pytest.raises(ValueError):
        make_grid([1, 2], [1], {"v": [[1], [3]]})


def test_grid_rejects_wrong_variant_shape():
    with pytest.raises(ValueError, match="v"):
        make_grid([1, 2], [1, 2, 3], {"v": [[1, 2], [3, 4]]})


def test_grid_rejects_transposed_variant():
    with pytest.raises(ValueError):
        make_grid([1, 2, 3], [1, 2], {"v": [[1, 2, 3], [4, 5, 6]]})


def test_grid_rejects_no_variants():
    with pytest.raises(ValueError):
        make_grid([1, 2], [1, 2], {})


# ---------------------------------------------------------------------------
# LabelMap
# ---------------------------------------------------------------------------

def test_valid_label_map_constructs():
    table = LabelMap(meta=make_meta(), values={"angular": 0.0, "round_gravel": 27.0})
    assert table.values["round_gravel"] == 27.0


def test_label_map_rejects_empty():
    with pytest.raises(ValueError):
        LabelMap(meta=make_meta(), values={})


# ===========================================================================
# M2 section: tables/interpolate.py
# ===========================================================================

from hypothesis import given
from hypothesis import strategies as st

from concretecalc.tables.interpolate import OutOfRangeError, _bracket, interp1d, interp2d

AXIS = np.array([10.0, 20.0, 40.0])


# --- _bracket ---------------------------------------------------------------

def test_bracket_inside_range():
    i0, t, status, warnings = _bracket(30.0, AXIS, "raise", "q")
    assert i0 == 1
    assert t == pytest.approx(0.5, abs=1e-15)
    assert status is Status.OK
    assert warnings == ()


def test_bracket_at_first_and_last_node_is_ok():
    i0, t, status, _ = _bracket(10.0, AXIS, "raise", "q")
    assert (i0, t, status) == (0, 0.0, Status.OK)
    # Last node: searchsorted(side="right") gives len(axis); clipping keeps the last segment, t = 1.
    i0, t, status, _ = _bracket(40.0, AXIS, "raise", "q")
    assert (i0, t, status) == (1, 1.0, Status.OK)


def test_bracket_at_inner_node_starts_new_segment():
    i0, t, _, _ = _bracket(20.0, AXIS, "raise", "q")
    assert (i0, t) == (1, 0.0)


def test_bracket_nan_query_raises():
    with pytest.raises(ValueError):
        _bracket(float("nan"), AXIS, "clamp", "q")


def test_bracket_unknown_policy_raises():
    with pytest.raises(ValueError):
        _bracket(15.0, AXIS, "nearest", "q")


@pytest.mark.parametrize("v", [5.0, 45.0])
def test_bracket_raise_policy(v):
    with pytest.raises(OutOfRangeError, match="q"):
        _bracket(v, AXIS, "raise", "q")


def test_out_of_range_error_is_a_value_error():
    assert issubclass(OutOfRangeError, ValueError)


def test_bracket_clamp_below_and_above():
    i0, t, status, warnings = _bracket(5.0, AXIS, "clamp", "slump_mm")
    assert (i0, t, status) == (0, 0.0, Status.CLAMPED)
    assert len(warnings) == 1
    # Message states the label, the value and the table range.
    assert "slump_mm" in warnings[0] and "5" in warnings[0] and "[10, 40]" in warnings[0]
    i0, t, status, _ = _bracket(45.0, AXIS, "clamp", "slump_mm")
    assert (i0, t, status) == (1, 1.0, Status.CLAMPED)


def test_bracket_extrapolate_uses_end_segments():
    i0, t, status, warnings = _bracket(5.0, AXIS, "extrapolate", "q")
    assert i0 == 0 and t == pytest.approx(-0.5, abs=1e-15) and status is Status.EXTRAPOLATED
    assert len(warnings) == 1
    i0, t, status, _ = _bracket(50.0, AXIS, "extrapolate", "q")
    assert i0 == 1 and t == pytest.approx(1.5, abs=1e-15) and status is Status.EXTRAPOLATED


# --- interp1d ----------------------------------------------------------------

XS = np.array([14.0, 21.0, 28.0])
YS = np.array([0.82, 0.68, 0.57])


def test_interp1d_exact_nodes():
    for x, y in zip(XS, YS):
        result = interp1d(x, XS, YS, "raise", "fcr_mpa")
        assert result.value == pytest.approx(y, abs=1e-15)
        assert result.status is Status.OK


def test_interp1d_midpoint():
    result = interp1d(17.5, XS, YS, "raise", "fcr_mpa")
    assert result.value == pytest.approx((0.82 + 0.68) / 2, abs=1e-15)


@pytest.mark.parametrize(
    "x, expected_value, expected_status",
    [
        (7.0, 0.82, Status.CLAMPED),
        (35.0, 0.57, Status.CLAMPED),
    ],
)
def test_interp1d_clamp(x, expected_value, expected_status):
    result = interp1d(x, XS, YS, "clamp", "fcr_mpa")
    assert result.value == pytest.approx(expected_value, abs=1e-15)
    assert result.status is expected_status
    assert len(result.warnings) == 1


def test_interp1d_extrapolate_both_ends():
    below = interp1d(7.0, XS, YS, "extrapolate", "fcr_mpa")
    # slope of first segment = (0.68 - 0.82)/7 = -0.02 per MPa -> 0.82 + 0.14 = 0.96
    assert below.value == pytest.approx(0.96, abs=1e-12)
    assert below.status is Status.EXTRAPOLATED
    above = interp1d(35.0, XS, YS, "extrapolate", "fcr_mpa")
    # last segment slope = (0.57 - 0.68)/7 -> 0.57 - 0.11 = 0.46
    assert above.value == pytest.approx(0.46, abs=1e-12)


def test_interp1d_raise_policy():
    with pytest.raises(OutOfRangeError):
        interp1d(50.0, XS, YS, "raise", "fcr_mpa")


def test_interp1d_drops_nan_points():
    # Like the AE column of the w/c table: no value at 48 MPa.
    xs = np.array([35.0, 41.0, 48.0])
    ys = np.array([0.40, 0.32, np.nan])
    result = interp1d(45.0, xs, ys, "extrapolate", "fcr_mpa")
    assert result.status is Status.EXTRAPOLATED  # 48 was dropped, so 45 is beyond 41
    assert result.value == pytest.approx(0.32 - 4 * (0.08 / 6), abs=1e-12)


def test_interp1d_inverts_a_decreasing_column():
    # Inversion: query by the w/c column (decreasing with strength) to get strength back.
    result = interp1d(0.68, YS, XS, "raise", "wc")
    assert result.value == pytest.approx(21.0, abs=1e-12)
    assert result.status is Status.OK
    middle = interp1d(0.625, YS, XS, "raise", "wc")
    assert middle.value == pytest.approx(24.5, abs=1e-12)


def test_interp1d_fewer_than_two_points_is_unavailable():
    result = interp1d(1.0, np.array([1.0, 2.0]), np.array([5.0, np.nan]), "clamp", "q")
    assert result.value is None
    assert result.status is Status.UNAVAILABLE
    assert len(result.warnings) == 1


def test_interp1d_repeated_x_raises():
    with pytest.raises(ValueError):
        interp1d(1.0, np.array([1.0, 1.0, 2.0]), np.array([1.0, 2.0, 3.0]), "clamp", "q")


def test_interp1d_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        interp1d(1.0, np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]), "clamp", "q")


def test_interp1d_returns_python_float():
    result = interp1d(17.5, XS, YS, "raise", "q")
    assert type(result.value) is float


@given(
    slope=st.floats(-100, 100),
    intercept=st.floats(-100, 100),
    x=st.floats(14.0, 28.0),
)
def test_interp1d_reproduces_linear_functions(slope, intercept, x):
    ys = slope * XS + intercept
    result = interp1d(x, XS, ys, "raise", "q")
    assert result.value == pytest.approx(slope * x + intercept, rel=1e-9, abs=1e-9)


@given(x=st.floats(14.0, 28.0))
def test_interp1d_value_lies_between_bracketing_points(x):
    result = interp1d(x, XS, YS, "raise", "q")
    assert min(YS) - 1e-12 <= result.value <= max(YS) + 1e-12


# --- interp2d ----------------------------------------------------------------

ROWS = np.array([37.5, 87.5, 162.5])
COLS = np.array([9.5, 12.5, 19.0])
GRID = np.array(
    [
        [207.0, 199.0, 190.0],
        [228.0, 216.0, 205.0],
        [243.0, 228.0, np.nan],
    ]
)


def i2(r, c, policy="raise"):
    return interp2d(r, c, ROWS, COLS, GRID, policy, "slump_mm", "nmas_mm")


def test_interp2d_exact_node():
    result = i2(87.5, 19.0)
    assert result.value == pytest.approx(205.0, abs=1e-12)
    assert result.status is Status.OK


def test_interp2d_on_row_between_columns():
    result = i2(87.5, 15.75)  # halfway between 12.5 and 19
    assert result.value == pytest.approx((216 + 205) / 2, abs=1e-12)


def test_interp2d_bilinear_centre():
    result = i2(62.5, 11.0)  # centre of the first cell
    assert result.value == pytest.approx((207 + 199 + 228 + 216) / 4, abs=1e-12)


def test_interp2d_null_corner_with_weight_is_unavailable():
    result = i2(125.0, 15.75)  # cell touching the NaN at (162.5, 19)
    assert result.value is None
    assert result.status is Status.UNAVAILABLE
    assert any("slump_mm" in w and "nmas_mm" in w for w in result.warnings)


def test_interp2d_null_exact_node_is_unavailable():
    assert i2(162.5, 19.0).status is Status.UNAVAILABLE


def test_interp2d_null_corner_with_zero_weight_is_ignored():
    # On the 162.5 row at 12.5 mm: the NaN neighbour (19 mm) has zero weight.
    result = i2(162.5, 12.5)
    assert result.value == pytest.approx(228.0, abs=1e-12)
    assert result.status is Status.OK
    # On the 19 mm column at 87.5: the NaN below (162.5 row) has zero weight.
    assert i2(87.5, 19.0).value == pytest.approx(205.0, abs=1e-12)


def test_interp2d_status_is_worst_of_both_axes():
    result = i2(10.0, 30.0, policy="clamp")  # both axes out of range -> both clamped
    assert result.status is Status.CLAMPED
    assert len(result.warnings) == 2
    assert result.value == pytest.approx(190.0, abs=1e-12)


def test_interp2d_clamped_row_extrapolated_col():
    # Policies apply to both axes; mixing comes from one axis being in range.
    result = i2(87.5, 25.0, policy="extrapolate")
    assert result.status is Status.EXTRAPOLATED
    # last column segment slope on row 87.5: (205-216)/6.5 per mm
    assert result.value == pytest.approx(205 + 6 * (205 - 216) / 6.5, abs=1e-12)


def test_interp2d_raise_policy():
    with pytest.raises(OutOfRangeError, match="nmas_mm"):
        i2(87.5, 25.0)


def test_interp2d_wrong_grid_shape_raises():
    with pytest.raises(ValueError):
        interp2d(50.0, 10.0, ROWS, COLS, GRID[:, :2], "clamp", "r", "c")  # 3x2 vs 3x3 axes


@given(
    a=st.floats(-10, 10),
    b=st.floats(-10, 10),
    c=st.floats(-10, 10),
    r=st.floats(37.5, 87.5),
    col=st.floats(9.5, 19.0),
)
def test_interp2d_reproduces_bilinear_functions(a, b, c, r, col):
    # f = a*r + b*col + c (planar) is reproduced exactly by bilinear interpolation.
    grid = a * ROWS[:, None] + b * COLS[None, :] + c
    result = interp2d(r, col, ROWS, COLS, grid, "raise", "r", "c")
    assert result.value == pytest.approx(a * r + b * col + c, rel=1e-9, abs=1e-9)


# ===========================================================================
# M3 section: data/*.json + tables/loader.py
# ===========================================================================

import json
from importlib.resources import files
from pathlib import Path

from concretecalc.tables.loader import list_table_ids, load_grid, load_mapping, load_series

SERIES_IDS = [
    "wc_vs_strength", "wc_vs_specified_fc", "air_content", "unit_weight", "f_factor", "min_cement_flatwork",
]
GRID_IDS = ["mixing_water", "bulk_volume_ca"]
MAPPING_IDS = [
    "mixing_water_slump_bands", "shape_reduction", "slump_ranges", "durability", "min_cement_misc",
    "age_coefficients", "standard_sieves", "required_strength_rules", "flag_thresholds",
]
ALL_IDS = SERIES_IDS + GRID_IDS + MAPPING_IDS
NMAS_AXIS = [9.5, 12.5, 19, 25, 37.5, 50, 75, 150]
REPO_ROOT = Path(__file__).resolve().parents[1]


def load_any(table_id):
    if table_id in SERIES_IDS:
        return load_series(table_id)
    if table_id in GRID_IDS:
        return load_grid(table_id)
    return load_mapping(table_id)


def test_list_table_ids_matches_the_data_folder():
    # M09 adds a separately validated presets envelope (approved D-3).
    assert set(list_table_ids()) == set(ALL_IDS) | {'model_constants'}
    assert list(list_table_ids()) == sorted(list_table_ids())


@pytest.mark.parametrize("table_id", ALL_IDS)
def test_every_table_loads_and_cites_a_source(table_id):
    table = load_any(table_id)
    assert table.meta.id == table_id
    assert table.meta.source.strip() != ""
    assert table.meta.title.strip() != ""
    # Ground rule 5 / task section 4: stays False until the owner verifies the table.
    assert table.meta.verified_against_primary is False


@pytest.mark.parametrize("table_id", ALL_IDS)
def test_every_table_appears_in_table_verification_doc(table_id):
    text = (REPO_ROOT / "docs" / "table_verification.md").read_text(encoding="utf-8")
    assert f"`{table_id}`" in text


@pytest.mark.parametrize("table_id", SERIES_IDS)
def test_series_tables_reject_the_wrong_loader(table_id):
    with pytest.raises(ValueError, match="kind"):
        load_grid(table_id)
    with pytest.raises(ValueError, match="kind"):
        load_mapping(table_id)


@pytest.mark.parametrize("table_id", GRID_IDS)
def test_grid_tables_reject_the_wrong_loader(table_id):
    with pytest.raises(ValueError, match="kind"):
        load_series(table_id)


@pytest.mark.parametrize("table_id", MAPPING_IDS)
def test_mapping_tables_reject_the_wrong_loader(table_id):
    with pytest.raises(ValueError, match="kind"):
        load_series(table_id)


def test_unknown_table_raises():
    with pytest.raises(FileNotFoundError):
        load_series("no_such_table")


def test_loader_is_cached():
    assert load_series("wc_vs_strength") is load_series("wc_vs_strength")
    assert load_grid("mixing_water") is load_grid("mixing_water")


def test_series_arrays_are_read_only():
    table = load_series("wc_vs_strength")
    with pytest.raises(ValueError):
        table.x[0] = 99.0
    with pytest.raises(ValueError):
        table.columns["non_ae"][0] = 99.0


def test_grid_arrays_are_read_only():
    table = load_grid("mixing_water")
    for array in (table.rows, table.cols, table.variants["non_ae"]):
        with pytest.raises(ValueError):
            array[0] = 0.0


PAYLOAD_KEYS = {"series": {"x", "series"}, "grid2d": {"rows", "cols", "variants"}, "mapping": {"values"}}


@pytest.mark.parametrize("table_id", ALL_IDS)
def test_json_files_follow_the_envelope_exactly(table_id):
    data_dir = files("concretecalc") / "data"
    raw = json.loads((data_dir / f"{table_id}.json").read_text(encoding="utf-8"))
    assert raw["kind"] in PAYLOAD_KEYS
    # Exactly meta + kind + the payload keys of that kind; nothing else.
    assert set(raw) == {"meta", "kind"} | PAYLOAD_KEYS[raw["kind"]]
    assert set(raw["meta"]) == {"id", "title", "source", "verified_against_primary", "units", "notes"}
    assert isinstance(raw["meta"]["verified_against_primary"], bool)


@pytest.mark.parametrize("table_id", ALL_IDS)
def test_no_zero_used_as_missing_marker_in_mixing_water_like_tables(table_id):
    # Task section 4: null means "no data"; 0 must never stand in for it. The only
    # legitimate zeros are the angular shape reduction and the 0 % soft-limit minima.
    raw = load_any(table_id)
    if table_id in ("shape_reduction", "flag_thresholds"):
        return
    if table_id in SERIES_IDS:
        arrays = list(raw.columns.values())
    elif table_id in GRID_IDS:
        arrays = list(raw.variants.values())
    else:
        arrays = [np.array(list(raw.values.values()))]
    for array in arrays:
        assert not np.any(array == 0.0)


# --- loader error paths (exercised on in-memory dicts; package data is valid) --

from concretecalc.tables import loader as loader_module

GOOD_META = {"id": "t", "title": "T", "source": "s", "verified_against_primary": False, "units": {}, "notes": ""}


def test_check_kind_rejects_wrong_or_missing_kind():
    with pytest.raises(ValueError, match="kind"):
        loader_module._check_kind({"kind": "grid2d"}, "t", "series")
    with pytest.raises(ValueError, match="kind"):
        loader_module._check_kind({}, "t", "series")
    loader_module._check_kind({"kind": "series"}, "t", "series")  # no error


def test_build_meta_requires_every_key():
    for key in GOOD_META:
        meta = dict(GOOD_META)
        del meta[key]
        with pytest.raises(ValueError, match=key):
            loader_module._build_meta({"meta": meta}, "t")


def test_build_meta_requires_meta_object():
    with pytest.raises(ValueError, match="meta"):
        loader_module._build_meta({}, "t")


def test_build_meta_requires_id_to_match_file_name():
    with pytest.raises(ValueError, match="must match"):
        loader_module._build_meta({"meta": dict(GOOD_META, id="other")}, "t")


def test_read_only_array_converts_null_to_nan():
    array = loader_module._read_only_array([1, None, 3])
    assert array.dtype == float
    assert np.isnan(array[1])
    assert array.flags.writeable is False


# --- full-table checks for the two tables everything depends on --------------

def test_wc_vs_strength_full_table():
    table = load_series("wc_vs_strength")
    assert table.x.tolist() == [14, 21, 28, 35, 41, 48]
    assert table.columns["non_ae"].tolist() == [0.82, 0.68, 0.57, 0.48, 0.41, 0.33]
    ae = table.columns["ae"]
    assert ae[:5].tolist() == [0.74, 0.59, 0.48, 0.40, 0.32]
    assert np.isnan(ae[5])  # null at 48 MPa


def test_mixing_water_full_table():
    table = load_grid("mixing_water")
    assert table.rows.tolist() == [37.5, 87.5, 162.5]
    assert table.cols.tolist() == NMAS_AXIS
    non_ae = table.variants["non_ae"]
    ae = table.variants["ae"]
    assert non_ae[0].tolist() == [207, 199, 190, 179, 166, 154, 130, 113]
    assert non_ae[1].tolist() == [228, 216, 205, 193, 181, 169, 145, 124]
    assert non_ae[2, :7].tolist() == [243, 228, 216, 202, 190, 178, 160]
    assert ae[0].tolist() == [181, 175, 168, 160, 150, 142, 122, 107]
    assert ae[1].tolist() == [202, 193, 184, 175, 165, 157, 133, 119]
    assert ae[2, :7].tolist() == [216, 205, 197, 184, 174, 166, 154]
    assert np.isnan(non_ae[2, 7]) and np.isnan(ae[2, 7])
    # Only those two cells are null.
    assert int(np.isnan(non_ae).sum()) == 1 and int(np.isnan(ae).sum()) == 1


# --- spot values for the remaining tables -------------------------------------

def test_wc_vs_specified_fc_spot_values():
    table = load_series("wc_vs_specified_fc")
    assert table.x.tolist() == [17, 21, 24, 28, 31]
    assert table.columns["non_ae"][0] == 0.67 and table.columns["non_ae"][4] == 0.38
    assert table.columns["ae"][3] == 0.35 and np.isnan(table.columns["ae"][4])


def test_air_content_spot_values():
    table = load_series("air_content")
    assert table.x.tolist() == NMAS_AXIS
    assert table.columns["non_ae"].tolist() == [3, 2.5, 2, 1.5, 1, 0.5, 0.3, 0.2]
    assert table.columns["ae_mild"][0] == 4.5 and table.columns["ae_mild"][7] == 1.0
    assert table.columns["ae_moderate"][2] == 5.0 and table.columns["ae_moderate"][4] == 4.5
    assert table.columns["ae_severe"][2] == 6.0 and table.columns["ae_severe"][3] == 6.0


def test_bulk_volume_spot_values():
    table = load_grid("bulk_volume_ca")
    assert table.rows.tolist() == NMAS_AXIS
    assert table.cols.tolist() == [2.40, 2.60, 2.80, 3.00]
    b = table.variants["b_b0"]
    assert b[0].tolist() == [0.50, 0.48, 0.46, 0.44]
    assert b[4, 1] == 0.73  # 37.5 mm, FM 2.6 (used by Example 1)
    assert b[7].tolist() == [0.87, 0.85, 0.83, 0.81]


def test_unit_weight_spot_values():
    table = load_series("unit_weight")
    assert table.columns["non_ae"][0] == 2276 and table.columns["ae"][0] == 2187
    assert table.columns["non_ae"][7] == 2507 and table.columns["ae"][7] == 2441


def test_f_factor_values():
    table = load_series("f_factor")
    assert table.x.tolist() == [15, 20, 25, 30]
    assert table.columns["f"].tolist() == [1.16, 1.08, 1.03, 1.00]


def test_min_cement_tables():
    flat = load_series("min_cement_flatwork")
    assert flat.x.tolist() == [9.5, 12.5, 19, 25, 37.5]
    assert flat.columns["min_cement_kg_m3"].tolist() == [360, 350, 320, 310, 280]
    misc = load_mapping("min_cement_misc")
    assert misc.values == {"severe_exposure": 334.0, "underwater": 385.0}


def test_shape_reduction_values():
    values = load_mapping("shape_reduction").values
    assert values == {"angular": 0.0, "subangular": 12.0, "gravel_with_crushed": 21.0, "round_gravel": 27.0}


def test_slump_ranges_values():
    values = load_mapping("slump_ranges").values
    assert values["beams_reinforced_walls.max_mm"] == 100
    assert values["building_columns.max_mm"] == 100
    assert values["pavements_slabs.max_mm"] == 75
    assert values["mass_concrete.hand_consolidation_extra_mm"] == 25
    mins = [v for k, v in values.items() if k.endswith(".min_mm")]
    assert len(mins) == 6 and set(mins) == {25.0}


def test_durability_values():
    values = load_mapping("durability").values
    assert values["low_permeability.max_wc"] == 0.50 and values["low_permeability.min_fc_psi"] == 4000
    assert values["freeze_thaw_moist.max_wc"] == 0.45 and values["freeze_thaw_moist.min_fc_psi"] == 4500
    assert values["corrosion_protection.max_wc"] == 0.40 and values["corrosion_protection.min_fc_psi"] == 5000
    assert values["full_hydration.min_wc_lower"] == 0.22 and values["full_hydration.min_wc_upper"] == 0.25


def test_age_coefficients_values():
    values = load_mapping("age_coefficients").values
    assert (values["moist.type_I.a_days"], values["moist.type_I.b"]) == (4.0, 0.85)
    assert (values["moist.type_III.a_days"], values["moist.type_III.b"]) == (2.3, 0.92)
    assert (values["steam.type_I.a_days"], values["steam.type_I.b"]) == (1.0, 0.95)
    assert (values["steam.type_III.a_days"], values["steam.type_III.b"]) == (0.7, 0.98)
    assert "ACI 209R-92" in load_mapping("age_coefficients").meta.source


def test_standard_sieves_and_bands():
    sieves = load_mapping("standard_sieves").values
    assert sorted(sieves.values()) == NMAS_AXIS
    bands = load_mapping("mixing_water_slump_bands").values
    # Midpoints of the bands must equal the mixing-water row axis.
    midpoints = [
        (bands["band_low.min_mm"] + bands["band_low.max_mm"]) / 2,
        (bands["band_mid.min_mm"] + bands["band_mid.max_mm"]) / 2,
        (bands["band_high.min_mm"] + bands["band_high.max_mm"]) / 2,
    ]
    assert midpoints == load_grid("mixing_water").rows.tolist()


def test_required_strength_rules_values():
    values = load_mapping("required_strength_rules").values
    assert values["statistical.coef_134"] == 1.34
    assert values["statistical.coef_233"] == 2.33
    assert values["statistical.offset_233_mpa"] == 3.45
    assert (values["no_data.margin_low_mpa"], values["no_data.margin_mid_mpa"], values["no_data.margin_high_mpa"]) == (7.0, 8.5, 10.0)
    assert values["no_data.low_band_below_mpa"] == 21 and values["no_data.mid_band_up_to_mpa"] == 35
    assert values["f_factor.min_n"] == 15


def test_flag_thresholds_spot_values():
    values = load_mapping("flag_thresholds").values
    assert values["volume_closure.warning_m3"] == 0.02 and values["volume_closure.error_m3"] == 0.05
    assert values["model_spread_mpa"] == 5
    assert values["slide_rule.air_entrainer_ml_per_pct_per_100kg"] == 6.3
    assert values["soft.cement_kg_m3.min"] == 150 and values["soft.cement_kg_m3.max"] == 700
    assert values["hard.mc_pct.max"] == 30
    # Every soft/hard key comes as a min/max pair (except the single hard age minimum).
    for key in values:
        if key.startswith("soft.") and key.endswith(".min"):
            assert key[:-4] + ".max" in values


def test_mapping_values_are_python_floats():
    for value in load_mapping("shape_reduction").values.values():
        assert type(value) is float


# ===========================================================================
# M4 section: tables/lookups.py
# ===========================================================================

from concretecalc.tables import lookups


# --- w/c tables ----------------------------------------------------------------

def test_wc_for_strength_nodes_and_midpoint():
    assert lookups.wc_for_strength(28.0, air_entrained=False).value == pytest.approx(0.57, abs=1e-12)
    assert lookups.wc_for_strength(28.0, air_entrained=True).value == pytest.approx(0.48, abs=1e-12)
    result = lookups.wc_for_strength(31.5, air_entrained=False)
    assert result.value == pytest.approx(0.525, abs=1e-12)
    assert result.status is Status.OK


def test_wc_for_strength_ae_48_is_dropped_so_45_is_extrapolated():
    result = lookups.wc_for_strength(45.0, air_entrained=True)
    assert result.status is Status.EXTRAPOLATED
    assert result.value == pytest.approx(0.32 - 4 * (0.08 / 6), abs=1e-12)
    # Same strength without air entrainment is inside the table.
    assert lookups.wc_for_strength(45.0, air_entrained=False).status is Status.OK


def test_wc_for_strength_policies():
    assert lookups.wc_for_strength(60.0, False, policy="clamp").value == pytest.approx(0.33, abs=1e-12)
    with pytest.raises(OutOfRangeError):
        lookups.wc_for_strength(60.0, False, policy="raise")


@pytest.mark.parametrize("air_entrained", [False, True])
@pytest.mark.parametrize("fcr_mpa", [14.0, 17.3, 21.0, 24.1, 28.0, 33.3, 35.0, 40.0, 41.0])
def test_strength_for_wc_inverts_wc_for_strength(air_entrained, fcr_mpa):
    wc = lookups.wc_for_strength(fcr_mpa, air_entrained).value
    back = lookups.strength_for_wc(wc, air_entrained)
    assert back.value == pytest.approx(fcr_mpa, abs=1e-9)
    assert back.status is Status.OK


def test_strength_for_wc_out_of_range_is_extrapolated():
    result = lookups.strength_for_wc(0.90, air_entrained=False)
    assert result.status is Status.EXTRAPOLATED
    # Last segment (0.68 -> 21, 0.82 -> 14): slope -50 MPa per unit w/c -> 14 - 0.08*50 = 10
    assert result.value == pytest.approx(10.0, abs=1e-9)


def test_wc_for_specified_fc():
    assert lookups.wc_for_specified_fc(24.0, False).value == pytest.approx(0.51, abs=1e-12)
    assert lookups.wc_for_specified_fc(24.0, True).value == pytest.approx(0.40, abs=1e-12)
    assert lookups.wc_for_specified_fc(31.0, True).status is Status.EXTRAPOLATED  # AE null at 31


# --- mixing water ----------------------------------------------------------------

def test_mixing_water_task_examples():
    # Required by the task (M4): (87.5 mm, 19 mm, non-AE, angular) = 205; (87.5, 22 mm) = 199.
    assert lookups.mixing_water_kg_m3(87.5, 19.0, False, "angular").value == pytest.approx(205.0, abs=1e-12)
    result = lookups.mixing_water_kg_m3(87.5, 22.0, False, "angular")
    assert result.value == pytest.approx(199.0, abs=1e-12)
    assert result.status is Status.OK


@pytest.mark.parametrize(
    "shape, reduction",
    [("angular", 0), ("subangular", 12), ("gravel_with_crushed", 21), ("round_gravel", 27)],
)
def test_mixing_water_shape_reduction(shape, reduction):
    result = lookups.mixing_water_kg_m3(87.5, 19.0, False, shape)
    assert result.value == pytest.approx(205.0 - reduction, abs=1e-12)


def test_mixing_water_air_entrained():
    assert lookups.mixing_water_kg_m3(87.5, 19.0, True, "angular").value == pytest.approx(184.0, abs=1e-12)
    assert lookups.mixing_water_kg_m3(37.5, 25.0, True, "round_gravel").value == pytest.approx(160.0 - 27.0, abs=1e-12)


def test_mixing_water_null_cell_is_unavailable():
    result = lookups.mixing_water_kg_m3(162.5, 150.0, False, "angular")
    assert result.value is None
    assert result.status is Status.UNAVAILABLE
    assert lookups.mixing_water_kg_m3(125.0, 100.0, True, "angular").status is Status.UNAVAILABLE
    # Neighbour of the null on the same row is fine.
    assert lookups.mixing_water_kg_m3(162.5, 75.0, False, "angular").value == pytest.approx(160.0, abs=1e-12)


def test_mixing_water_interpolates_between_midpoints():
    # 75 mm with pure midpoint interpolation: 190 + 0.75 * (205 - 190) = 201.25 (OPEN_QUESTIONS Q26)
    result = lookups.mixing_water_kg_m3(75.0, 19.0, False, "angular")
    assert result.value == pytest.approx(201.25, abs=1e-12)


def test_mixing_water_default_policy_is_clamp():
    result = lookups.mixing_water_kg_m3(200.0, 19.0, False, "angular")
    assert result.status is Status.CLAMPED
    assert result.value == pytest.approx(216.0, abs=1e-12)


# Band reading (D-2): inside a band -> that row; between bands -> linear between band edges.
@pytest.mark.parametrize(
    "slump_mm, expected",
    [
        (25.0, 190.0), (37.5, 190.0), (50.0, 190.0),       # low band
        (60.0, 190.0 + 0.4 * 15.0),                          # between 50 and 75: t = 10/25
        (75.0, 205.0), (87.5, 205.0), (100.0, 205.0),        # mid band
        (120.0, 205.0 + 0.4 * 11.0),                         # between 100 and 150: t = 20/50
        (150.0, 216.0), (175.0, 216.0),                      # high band
    ],
)
def test_mixing_water_band_reading(slump_mm, expected):
    result = lookups.mixing_water_kg_m3(slump_mm, 19.0, False, "angular", slump_lookup="band")
    assert result.value == pytest.approx(expected, abs=1e-12)
    assert result.status is Status.OK


def test_mixing_water_band_reading_outside_bands():
    below = lookups.mixing_water_kg_m3(10.0, 19.0, False, "angular", slump_lookup="band")
    assert below.status is Status.CLAMPED and below.value == pytest.approx(190.0, abs=1e-12)
    above = lookups.mixing_water_kg_m3(200.0, 19.0, False, "angular", slump_lookup="band", policy="extrapolate")
    # Band reading never extrapolates a band; it uses the end row and says so.
    assert above.status is Status.CLAMPED and above.value == pytest.approx(216.0, abs=1e-12)
    with pytest.raises(OutOfRangeError):
        lookups.mixing_water_kg_m3(10.0, 19.0, False, "angular", slump_lookup="band", policy="raise")


def test_mixing_water_band_reading_null_row_is_unavailable():
    assert lookups.mixing_water_kg_m3(160.0, 150.0, False, "angular", slump_lookup="band").status is Status.UNAVAILABLE
    # Between bands next to the null row also needs it.
    assert lookups.mixing_water_kg_m3(120.0, 150.0, False, "angular", slump_lookup="band").status is Status.UNAVAILABLE
    assert lookups.mixing_water_kg_m3(90.0, 150.0, False, "angular", slump_lookup="band").value == pytest.approx(124.0, abs=1e-12)


def test_mixing_water_band_reading_off_node_nmas():
    result = lookups.mixing_water_kg_m3(75.0, 22.0, False, "angular", slump_lookup="band")
    assert result.value == pytest.approx(199.0, abs=1e-12)


def test_mixing_water_rejects_unknown_options():
    with pytest.raises(ValueError):
        lookups.mixing_water_kg_m3(75.0, 19.0, False, "angular", slump_lookup="nearest")
    with pytest.raises(ValueError):
        lookups.mixing_water_kg_m3(75.0, 19.0, False, "crushed")


# --- slump from water (inverse) ----------------------------------------------------

@pytest.mark.parametrize("air_entrained", [False, True])
@pytest.mark.parametrize("nmas_mm", [9.5, 19.0, 22.0, 37.5, 75.0])
@pytest.mark.parametrize("shape", ["angular", "round_gravel"])
@pytest.mark.parametrize("slump_mm", [37.5, 87.5, 162.5])
def test_slump_for_water_inverts_mixing_water_at_midpoints(air_entrained, nmas_mm, shape, slump_mm):
    water = lookups.mixing_water_kg_m3(slump_mm, nmas_mm, air_entrained, shape).value
    result = lookups.slump_for_water_mm(water, nmas_mm, air_entrained, shape)
    assert result.value == pytest.approx(slump_mm, abs=1e-9)
    assert result.status is Status.OK


@given(slump_mm=st.floats(37.5, 162.5), nmas_mm=st.floats(9.5, 75.0))
def test_slump_for_water_round_trip_inside_table(slump_mm, nmas_mm):
    water = lookups.mixing_water_kg_m3(slump_mm, nmas_mm, False, "subangular").value
    back = lookups.slump_for_water_mm(water, nmas_mm, False, "subangular")
    assert back.value == pytest.approx(slump_mm, abs=1e-9)


def test_slump_for_water_150mm_uses_two_rows():
    result = lookups.slump_for_water_mm(124.0, 150.0, False, "angular")
    assert result.value == pytest.approx(87.5, abs=1e-12)
    assert any("150-175" in w or "162.5" in w for w in result.warnings)
    beyond = lookups.slump_for_water_mm(130.0, 150.0, False, "angular")
    assert beyond.status is Status.EXTRAPOLATED
    assert beyond.value == pytest.approx(87.5 + 6.0 * 50.0 / 11.0, abs=1e-9)


def test_slump_for_water_extrapolates_by_default():
    result = lookups.slump_for_water_mm(170.0, 19.0, False, "angular")
    assert result.status is Status.EXTRAPOLATED
    # First segment: 190 -> 37.5, 205 -> 87.5 ; 20 kg/m3 below 190 -> 37.5 - 20 * 50/15
    assert result.value == pytest.approx(37.5 - 20.0 * 50.0 / 15.0, abs=1e-9)


# --- other tables -------------------------------------------------------------------

def test_shape_reduction_lookup():
    assert lookups.shape_reduction_kg_m3("gravel_with_crushed").value == 21.0
    with pytest.raises(ValueError):
        lookups.shape_reduction_kg_m3("crushed")


def test_air_content():
    assert lookups.air_content_pct(19.0, "moderate", True).value == pytest.approx(5.0, abs=1e-12)
    assert lookups.air_content_pct(37.5, "severe", True).value == pytest.approx(5.5, abs=1e-12)
    assert lookups.air_content_pct(19.0, None, False).value == pytest.approx(2.0, abs=1e-12)
    # Exposure is ignored for non-AE concrete (entrapped air only).
    assert lookups.air_content_pct(19.0, "severe", False).value == pytest.approx(2.0, abs=1e-12)
    assert lookups.air_content_pct(22.0, None, False).value == pytest.approx(1.75, abs=1e-12)
    clamped = lookups.air_content_pct(200.0, "mild", True)
    assert clamped.status is Status.CLAMPED and clamped.value == pytest.approx(1.0, abs=1e-12)


def test_air_content_needs_exposure_when_air_entrained():
    with pytest.raises(ValueError, match="exposure"):
        lookups.air_content_pct(19.0, None, True)
    with pytest.raises(ValueError):
        lookups.air_content_pct(19.0, "extreme", True)


def test_bulk_volume_ratio():
    assert lookups.bulk_volume_ratio(37.5, 2.6).value == pytest.approx(0.73, abs=1e-12)
    assert lookups.bulk_volume_ratio(19.0, 2.7).value == pytest.approx(0.63, abs=1e-12)
    extrapolated = lookups.bulk_volume_ratio(19.0, 3.2)
    assert extrapolated.status is Status.EXTRAPOLATED
    assert extrapolated.value == pytest.approx(0.58, abs=1e-12)


def test_fresh_unit_weight():
    assert lookups.fresh_unit_weight_kg_m3(19.0, True).value == pytest.approx(2276.0, abs=1e-12)
    assert lookups.fresh_unit_weight_kg_m3(22.0, False).value == pytest.approx(2361.5, abs=1e-12)


def test_slump_limits():
    low, high = lookups.slump_limits_mm("beams_reinforced_walls")
    assert (low.value, high.value) == (25.0, 100.0)
    low, high = lookups.slump_limits_mm("pavements_slabs")
    assert (low.value, high.value) == (25.0, 75.0)
    with pytest.raises(ValueError):
        lookups.slump_limits_mm("bridge_pier")


def test_hand_consolidation_allowance():
    assert lookups.hand_consolidation_extra_mm().value == 25.0


@pytest.mark.parametrize("n, expected", [(15, 1.16), (17, 1.128), (20, 1.08), (25, 1.03), (30, 1.00), (45, 1.00)])
def test_f_factor(n, expected):
    result = lookups.f_factor(n)
    assert result.value == pytest.approx(expected, abs=1e-12)
    assert result.status is Status.OK  # F = 1.00 for n >= 30 is the rule, not a clamp


def test_f_factor_below_15_is_unavailable():
    result = lookups.f_factor(14)
    assert result.value is None and result.status is Status.UNAVAILABLE
    assert "unknown" in result.warnings[0]
    with pytest.raises(ValueError):
        lookups.f_factor(-1)


def test_durability():
    assert lookups.max_wc_durability("freeze_thaw_moist").value == pytest.approx(0.45, abs=1e-12)
    none_class = lookups.max_wc_durability("none")
    assert none_class.value is None and none_class.status is Status.OK
    assert lookups.min_fc_durability_mpa("freeze_thaw_moist").value == pytest.approx(31.026407805, abs=1e-9)
    assert lookups.min_fc_durability_mpa("low_permeability").value == pytest.approx(27.57902916, abs=1e-8)
    assert lookups.min_fc_durability_mpa("none").value is None
    with pytest.raises(ValueError):
        lookups.max_wc_durability("marine")


def test_full_hydration_limits():
    low, high = lookups.full_hydration_wc_limits()
    assert (low.value, high.value) == (0.22, 0.25)


def test_min_cement_flatwork():
    assert lookups.min_cement_flatwork_kg_m3(19.0).value == pytest.approx(320.0, abs=1e-12)
    assert lookups.min_cement_flatwork_kg_m3(22.0).value == pytest.approx(315.0, abs=1e-12)
    above = lookups.min_cement_flatwork_kg_m3(50.0)
    assert above.value is None and above.status is Status.UNAVAILABLE


def test_min_cement_misc():
    assert lookups.min_cement_misc_kg_m3("severe_exposure").value == 334.0
    assert lookups.min_cement_misc_kg_m3("underwater").value == 385.0
    with pytest.raises(ValueError):
        lookups.min_cement_misc_kg_m3("marine")


def test_standard_sieves():
    assert lookups.standard_sieves_mm() == (9.5, 12.5, 19.0, 25.0, 37.5, 50.0, 75.0, 150.0)
    assert lookups.is_standard_nmas(19.0) is True
    assert lookups.is_standard_nmas(22.0) is False


def test_threshold_lookup():
    assert lookups.threshold("model_spread_mpa") == 5.0
    with pytest.raises(KeyError):
        lookups.threshold("no_such_threshold")


def test_required_strength_rule_lookup():
    assert lookups.required_strength_rule("statistical.coef_233") == 2.33
    with pytest.raises(KeyError):
        lookups.required_strength_rule("nope")


def test_table_ranges_come_from_the_tables():
    assert lookups.strength_table_range_mpa() == (14.0, 48.0)
    assert lookups.fm_table_range() == (2.40, 3.00)
