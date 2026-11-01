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
