"""Data containers for reference tables and the result of a table lookup.

Everything here is plain data plus load-time validation. No interpolation and
no file reading happen in this module (see interpolate.py and loader.py).

The three table shapes mirror the JSON "kind" field (PLAN.md, M3):
    series -> Series1D : one numeric axis x, several named columns
    grid2d -> Grid2D   : two numeric axes (rows, cols), several named 2-D variants
    mapping -> LabelMap: label -> number
Missing data is NaN (JSON null). Axes may never contain NaN.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np


class Status(str, Enum):
    """How trustworthy a looked-up value is, from best to worst.

    Inheriting from str makes Status.OK == "ok" and lets reports be written
    to JSON without special handling.
    """

    OK = "ok"                        # inside the table range
    CLAMPED = "clamped"              # query was outside the range; end value used
    EXTRAPOLATED = "extrapolated"    # query was outside the range; end segment extended
    UNAVAILABLE = "unavailable"      # no value (null cell or not enough data)


# Severity rank used by worst(). A plain dict keeps the ordering explicit and
# independent of the declaration order of the Enum members.
_SEVERITY_RANK = {
    Status.OK: 0,
    Status.CLAMPED: 1,
    Status.EXTRAPOLATED: 2,
    Status.UNAVAILABLE: 3,
}


def worst(*statuses: Status) -> Status:
    """Return the most severe status (OK < CLAMPED < EXTRAPOLATED < UNAVAILABLE).

    With no arguments the result is Status.OK (nothing went wrong; ASSUMPTIONS A-01).
    Raises TypeError if an argument is not a Status: a bare string such as "ok"
    compares equal to Status.OK, so we check the type explicitly to catch
    programmer errors early.
    """
    result = Status.OK
    for status in statuses:
        if not isinstance(status, Status):
            raise TypeError(f"worst() expects Status values, got {status!r}")
        if _SEVERITY_RANK[status] > _SEVERITY_RANK[result]:
            result = status
    return result


@dataclass(frozen=True)
class Lookup:
    """Result of one table lookup.

    value    : the number in the table's units, or None when unavailable.
    status   : see Status.
    warnings : human-readable messages (label, value, table range); data, never printed.
    """

    value: float | None
    status: Status
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TableMeta:
    """The "meta" block of a JSON table file, field for field.

    verified_against_primary stays False until the owner has checked every value
    against ACI 211.1 / PCA (docs/table_verification.md).
    """

    id: str
    title: str
    source: str
    verified_against_primary: bool
    units: dict[str, str]
    notes: str


def _check_axis(axis: np.ndarray, axis_name: str, table_id: str) -> None:
    """Raise ValueError unless axis is 1-D, has >= 2 points and is strictly increasing.

    Interpolation (interpolate.py) relies on all three properties, so a table
    that breaks them must fail when it is loaded, not later during a lookup.
    """
    if axis.ndim != 1:
        raise ValueError(f"table '{table_id}': axis '{axis_name}' must be 1-D, got shape {axis.shape}")
    if axis.size < 2:
        raise ValueError(f"table '{table_id}': axis '{axis_name}' needs at least 2 points, got {axis.size}")
    if np.any(np.isnan(axis)):
        raise ValueError(f"table '{table_id}': axis '{axis_name}' contains NaN (null); axes must be complete")
    steps = np.diff(axis)
    if np.any(steps <= 0):
        raise ValueError(f"table '{table_id}': axis '{axis_name}' must be strictly increasing, got {axis.tolist()}")


# eq=False: numpy arrays do not support "==" returning a single bool, so the
# auto-generated __eq__ would be misleading. Identity comparison is enough.
@dataclass(frozen=True, eq=False)
class Series1D:
    """Table with one numeric axis `x` and named columns of the same length."""

    meta: TableMeta
    x: np.ndarray
    columns: dict[str, np.ndarray]

    def __post_init__(self) -> None:
        table_id = self.meta.id
        _check_axis(self.x, "x", table_id)
        if len(self.columns) == 0:
            raise ValueError(f"table '{table_id}': a series table needs at least one column")
        for name, values in self.columns.items():
            if values.shape != self.x.shape:
                raise ValueError(
                    f"table '{table_id}': column '{name}' has shape {values.shape}, "
                    f"expected {self.x.shape} to match axis x"
                )


@dataclass(frozen=True, eq=False)
class Grid2D:
    """Table with two numeric axes (`rows`, `cols`) and named 2-D variants.

    variants[name][i, j] is the value at rows[i], cols[j].
    """

    meta: TableMeta
    rows: np.ndarray
    cols: np.ndarray
    variants: dict[str, np.ndarray]

    def __post_init__(self) -> None:
        table_id = self.meta.id
        _check_axis(self.rows, "rows", table_id)
        _check_axis(self.cols, "cols", table_id)
        if len(self.variants) == 0:
            raise ValueError(f"table '{table_id}': a grid table needs at least one variant")
        expected_shape = (self.rows.size, self.cols.size)
        for name, values in self.variants.items():
            if values.shape != expected_shape:
                raise ValueError(
                    f"table '{table_id}': variant '{name}' has shape {values.shape}, "
                    f"expected {expected_shape} (rows x cols)"
                )


@dataclass(frozen=True)
class LabelMap:
    """Table that maps a text label to a number (JSON kind "mapping").

    Named LabelMap, not Mapping, to avoid clashing with typing.Mapping.
    """

    meta: TableMeta
    values: dict[str, float]

    def __post_init__(self) -> None:
        if len(self.values) == 0:
            raise ValueError(f"table '{self.meta.id}': a mapping table needs at least one label")
