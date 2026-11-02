"""Linear (1-D) and bilinear (2-D) table interpolation: the single numeric primitive.

Every table lookup in the engine goes through interp1d or interp2d (called only
from tables/lookups.py). Both share one helper, _bracket, which finds the table
segment around a query value and applies the out-of-range policy:

    "raise"       -> OutOfRangeError
    "clamp"       -> use the nearest end value,          Status.CLAMPED
    "extrapolate" -> extend the nearest end segment,     Status.EXTRAPOLATED

Values exactly on the first or last node are inside the range (Status.OK).
"""

from typing import Literal

import numpy as np

from concretecalc.tables.models import Lookup, Status, worst

Policy = Literal["clamp", "extrapolate", "raise"]

_POLICIES = ("clamp", "extrapolate", "raise")


class OutOfRangeError(ValueError):
    """Query outside the table range while policy == "raise"."""


def _bracket(v: float, axis: np.ndarray, policy: Policy, label: str) -> tuple[int, float, Status, tuple[str, ...]]:
    """Locate v on a strictly increasing axis.

    Returns (i0, t, status, warnings) such that the interpolated value is
        y = y[i0] + t * (y[i0 + 1] - y[i0])
    t is in [0, 1] inside the range; with "extrapolate" it may be < 0 or > 1.

    i0 = clip(searchsorted(axis, v, side="right") - 1, 0, len(axis) - 2)
    t  = (v - axis[i0]) / (axis[i0 + 1] - axis[i0])
    """
    if policy not in _POLICIES:
        raise ValueError(f"unknown out-of-range policy {policy!r}; expected one of {_POLICIES}")
    if np.isnan(v):
        raise ValueError(f"{label} is NaN; a table cannot be queried with NaN")

    low = float(axis[0])
    high = float(axis[-1])
    status = Status.OK
    warnings: tuple[str, ...] = ()
    query = float(v)

    if query < low or query > high:
        range_text = f"{label}={query:g} outside table range [{low:g}, {high:g}]"
        if policy == "raise":
            raise OutOfRangeError(range_text)
        if policy == "clamp":
            # Clip to the nearest end so t lands exactly on 0 or 1.
            if query < low:
                query = low
            else:
                query = high
            status = Status.CLAMPED
            warnings = (f"{range_text} (clamped to {query:g})",)
        else:
            # "extrapolate": keep the query; t will fall outside [0, 1] on the end segment.
            status = Status.EXTRAPOLATED
            warnings = (f"{range_text} (extrapolated linearly from the end segment)",)

    last_segment = len(axis) - 2
    i0 = int(np.searchsorted(axis, query, side="right")) - 1
    # Clip so a query on (or beyond) either end still uses a real segment.
    if i0 < 0:
        i0 = 0
    if i0 > last_segment:
        i0 = last_segment
    x0 = float(axis[i0])
    x1 = float(axis[i0 + 1])
    t = (query - x0) / (x1 - x0)
    return i0, t, status, warnings


def interp1d(x: float, xs: np.ndarray, ys: np.ndarray, policy: Policy, label: str) -> Lookup:
    """Linear interpolation of ys(xs) at x.

    - Pairs where xs or ys is NaN (JSON null) are dropped first.
    - The remaining pairs are sorted by xs, so a decreasing column can be used
      as xs to invert a table (e.g. w/c -> strength).
    - Fewer than 2 remaining points -> Lookup(None, UNAVAILABLE) (ASSUMPTIONS A-02).
    - Repeated xs after sorting -> ValueError (cannot interpolate / invert).
    Equation: y = ys[i0] + t * (ys[i0+1] - ys[i0]), with i0, t from _bracket.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    if xs.shape != ys.shape or xs.ndim != 1:
        raise ValueError(f"{label}: xs and ys must be 1-D arrays of the same length, got {xs.shape} and {ys.shape}")

    keep = ~(np.isnan(xs) | np.isnan(ys))
    xs_clean = xs[keep]
    ys_clean = ys[keep]
    if xs_clean.size < 2:
        message = f"{label}: fewer than 2 table points with data; no value available"
        return Lookup(value=None, status=Status.UNAVAILABLE, warnings=(message,))

    order = np.argsort(xs_clean, kind="stable")
    xs_sorted = xs_clean[order]
    ys_sorted = ys_clean[order]
    if np.any(np.diff(xs_sorted) <= 0):
        raise ValueError(f"{label}: interpolation axis has repeated values {xs_sorted.tolist()}")

    i0, t, status, warnings = _bracket(x, xs_sorted, policy, label)
    y0 = float(ys_sorted[i0])
    y1 = float(ys_sorted[i0 + 1])
    value = y0 + t * (y1 - y0)
    return Lookup(value=value, status=status, warnings=warnings)


def interp2d(
    r: float,
    c: float,
    rows: np.ndarray,
    cols: np.ndarray,
    grid: np.ndarray,
    policy: Policy,
    row_label: str,
    col_label: str,
) -> Lookup:
    """Bilinear interpolation of grid(rows, cols) at (r, c).

    Weights of the 4 surrounding cells = outer([1 - tr, tr], [1 - tc, tc]).
    Only corners with a non-zero weight need data: on a node or along a grid
    line, a NaN neighbour with zero weight is ignored. A NaN corner with
    non-zero weight gives Lookup(None, UNAVAILABLE).
    The same policy applies to both axes; status = worst(row status, col status).
    """
    rows = np.asarray(rows, dtype=float)
    cols = np.asarray(cols, dtype=float)
    grid = np.asarray(grid, dtype=float)
    expected_shape = (rows.size, cols.size)
    if grid.shape != expected_shape:
        raise ValueError(f"grid shape {grid.shape} does not match axes {expected_shape} (rows x cols)")

    i0, tr, row_status, row_warnings = _bracket(r, rows, policy, row_label)
    j0, tc, col_status, col_warnings = _bracket(c, cols, policy, col_label)
    status = worst(row_status, col_status)
    warnings = row_warnings + col_warnings

    row_weights = [1.0 - tr, tr]
    col_weights = [1.0 - tc, tc]
    total = 0.0
    for di in range(2):
        for dj in range(2):
            weight = row_weights[di] * col_weights[dj]
            if weight == 0.0:
                continue  # this corner does not influence the result
            corner = float(grid[i0 + di, j0 + dj])
            if np.isnan(corner):
                message = (
                    f"no table data near {row_label}={float(r):g}, {col_label}={float(c):g} "
                    f"(null cell at {row_label}={float(rows[i0 + di]):g}, {col_label}={float(cols[j0 + dj]):g})"
                )
                return Lookup(value=None, status=Status.UNAVAILABLE, warnings=warnings + (message,))
            total = total + weight * corner

    return Lookup(value=total, status=status, warnings=warnings)
