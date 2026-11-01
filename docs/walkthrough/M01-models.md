# M01 - tables/models.py: table containers and lookup results

## What this milestone adds

| File | Purpose |
|---|---|
| `src/concretecalc/tables/__init__.py` | Marks `tables` as a sub-package (docstring only). |
| `src/concretecalc/tables/models.py` | Data containers for reference tables plus the `Lookup` result type. |
| `tests/test_tables.py` | 44 tests for the above. Later milestones add sections to the same file. |

No numbers from the slides appear yet. This milestone only defines the shapes the numbers will live in.

## The pieces, one by one

### `Status` (an Enum that is also a `str`)
Every table lookup ends in one of four states:

| Status | Meaning | Example |
|---|---|---|
| `OK` | query inside the table range | water for 19 mm NMAS at 87.5 mm slump |
| `CLAMPED` | outside the range; the end value was used | slump 200 mm, so the 162.5 mm row is used |
| `EXTRAPOLATED` | outside the range; the end segment was extended | w/c for 45 MPa air-entrained (the table stops at 41) |
| `UNAVAILABLE` | no number exists | 150 mm NMAS at 150-175 mm slump (null in the slides) |

*Why a `str` Enum?* `Status.OK == "ok"` is true, so a report can be dumped to JSON and read back without a custom encoder.

### `worst(*statuses)`
Returns the most severe status, following OK < CLAMPED < EXTRAPOLATED < UNAVAILABLE.
A 2-D lookup has two axes. If the row was clamped and the column extrapolated, the result is
`worst(CLAMPED, EXTRAPOLATED) = EXTRAPOLATED`. The severity order sits in a small dict
(`_SEVERITY_RANK`), so it is visible in one place and does not depend on the order the Enum
members are written in.
Two details:
- `worst()` with no arguments gives `OK` (assumption A-01: nothing reported, nothing wrong).
- Passing the plain string `"ok"` raises `TypeError`. Because `"ok" == Status.OK`, a typo could
  otherwise slip through silently, and failing loudly is safer.

### `Lookup(value, status, warnings=())`
What every domain lookup (M4) returns. `value` is `None` only when the status is `UNAVAILABLE`.
`warnings` are sentences meant for the report. Ground rule 3: warnings are data, never `print`.

### `TableMeta`
A one-to-one copy of the JSON `"meta"` block: `id, title, source, verified_against_primary,
units, notes`. Keeping the field names identical to the JSON keys means the loader (M3) can
build it with no renaming logic.

### `Series1D`, `Grid2D`, `LabelMap`
| Class | JSON kind | Holds | Will be used for |
|---|---|---|---|
| `Series1D(meta, x, columns)` | series | one numeric axis + named columns | w/c vs f'cr, air content, unit weight, F-factor |
| `Grid2D(meta, rows, cols, variants)` | grid2d | two numeric axes + named 2-D arrays | mixing water (slump x NMAS), b/b0 (NMAS x FM) |
| `LabelMap(meta, values)` | mapping | label -> number | shape reduction, durability, age coefficients |

**Validation in `__post_init__`.** Interpolation (M2) assumes each axis is 1-D, has at least 2
points and is strictly increasing. A table breaking any of these would give wrong numbers
silently, so it must fail when it is constructed (that is, when the JSON is loaded). The helper
`_check_axis` does the three checks and also rejects NaN in an axis. NaN is allowed in data
cells, because JSON `null` means "no data", but an axis with a hole has no meaning.
Each column/variant must have exactly the axis shape. A transposed grid, (cols x rows) instead
of (rows x cols), is caught by this check.

**Why `frozen=True, eq=False`** for the array-holding classes: frozen stops anyone from
re-assigning a field after loading. `eq=False` is needed because the automatic `__eq__` would
compare numpy arrays with `==`, which returns an array instead of `True`/`False`. Making the
arrays themselves read-only is the loader's job in M3, because `frozen` protects the
attribute, not the array contents.

## Design notes / deviations
- None from PLAN.md. Assumptions used: A-01, A-24, A-38 (unchanged).

## Exercises (do by hand, then check in a Python shell)
1. What does `worst(Status.CLAMPED, Status.OK, Status.CLAMPED)` return? And `worst()`? Explain
   why each answer makes sense for a 2-D lookup whose row axis was clamped.
2. Will this construct or raise? If it raises, which check fires and what does the message say?
   `Series1D(meta, x=np.array([9.5, 12.5, 19.0, 19.0]), columns={"non_ae": np.array([3, 2.5, 2, 1.5])})`
3. The mixing-water table has 3 slump rows and 8 NMAS columns. Write down the shape a variant
   array must have. Then say what happens if someone writes it with 8 rows and 3 columns.
