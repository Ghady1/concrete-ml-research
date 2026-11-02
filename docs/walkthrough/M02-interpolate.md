# M02 - tables/interpolate.py: the one interpolation primitive

## What this milestone adds

| File | Purpose |
|---|---|
| `src/concretecalc/tables/interpolate.py` | `Policy`, `OutOfRangeError`, `_bracket`, `interp1d`, `interp2d` |
| `tests/test_tables.py` (M2 section) | 35 tests, 3 of them hypothesis property tests |

Every table number the engine uses will pass through these functions, called only from
`tables/lookups.py` (M4). Keeping one primitive means one place to test edge cases.

## `_bracket(v, axis, policy, label) -> (i0, t, status, warnings)`
Finds the segment `[axis[i0], axis[i0+1]]` that contains `v` and how far along it `v` sits:

    i0 = clip(searchsorted(axis, v, side="right") - 1, 0, len(axis) - 2)
    t  = (v - axis[i0]) / (axis[i0+1] - axis[i0])

*Why `side="right"` and the clip?* For a value exactly on an inner node, e.g. 20 on [10, 20, 40],
`searchsorted(..., "right")` returns 2, so i0 = 1 and t = 0: the node starts the next segment.
For the last node (40) it returns 3, so i0 = 2, which is clipped to 1 and gives t = 1. Either way
the result equals the node value, and no index runs off the end.

Out-of-range handling (`policy`):

| policy | what happens to `v` | status | t |
|---|---|---|---|
| `"raise"` | `OutOfRangeError` (a `ValueError`) | - | - |
| `"clamp"` | replaced by the nearest end | `CLAMPED` | exactly 0 or 1 |
| `"extrapolate"` | kept | `EXTRAPOLATED` | < 0 or > 1, on the end segment |

The warning text always contains the label, the value and the range, e.g.
`slump_mm=5 outside table range [10, 40] (clamped to 10)`. NaN queries and unknown policies
raise `ValueError`: both are programmer errors, not data conditions.

## `interp1d(x, xs, ys, policy, label) -> Lookup`
1. Drop pairs where `xs` or `ys` is NaN. This is how the air-entrained w/c column loses its
   48 MPa null, so a 45 MPa AE query becomes EXTRAPOLATED, as the task requires.
2. Sort the pairs by `xs`. This makes **inversion** free: pass the w/c column as `xs` and the
   strength axis as `ys`. The w/c column decreases with strength, but after sorting it is an
   ordinary increasing axis.
3. Fewer than 2 points left: `Lookup(None, UNAVAILABLE)` (A-02). Repeated `xs`: `ValueError`
   (a column with two equal w/c values cannot be inverted).
4. `y = y0 + t (y1 - y0)`.

Small deviation from the PLAN wording: the plan said "drop NaN ys". The code drops a pair if
*either* value is NaN, because during inversion the `xs` are a data column that may contain
nulls. When `xs` is a real axis it never contains NaN, so behaviour there is identical.

## `interp2d(r, c, rows, cols, grid, policy, row_label, col_label) -> Lookup`
Bilinear: bracket each axis separately, then weight the four surrounding cells by
`outer([1-tr, tr], [1-tc, tc])`, i.e. corner (di, dj) gets `rowweight[di] * colweight[dj]`.
The four weights always add up to 1.

**Null cells.** Only corners with non-zero weight are read. Example from the mixing-water
table: (162.5 mm slump, 150 mm NMAS) is null. A query exactly at (162.5, 75) gives the 75 mm
column weight 1 and the 150 mm column weight 0, so it still works. A query at (162.5, 100) needs
the null, so it returns `UNAVAILABLE` with a message naming the null cell.

Status = `worst(row status, col status)`. Both axes use the same policy.

## Exercises
1. Axis [10, 20, 40]. By hand, give (i0, t) for v = 30, v = 20, v = 40, and v = 50 with
   `"extrapolate"`. Then check with `_bracket`.
2. Interpolate the w/c table (non-AE: f'cr 28 -> 0.57, 35 -> 0.48) at f'cr = 31.5 MPa. Then
   invert: which f'cr gives w/c = 0.50? Verify with `interp1d(0.50, wc_column, fcr_axis, "raise", "wc")`.
3. Bilinear by hand: mixing water at slump 62.5 mm (midway between 37.5 and 87.5) and NMAS
   15.75 mm (midway between 12.5 and 19), non-AE: corners 199, 190, 216, 205. Which weights
   does each corner get, and what is the result?
