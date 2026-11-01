"""Load the versioned JSON reference tables from src/concretecalc/data/.

File format (PLAN.md M3):
    {"meta": {id, title, source, verified_against_primary, units, notes},
     "kind": "series" | "grid2d" | "mapping",
     ...payload...}
    series : "x": [...], "series": {"name": [...]}
    grid2d : "rows": [...], "cols": [...], "variants": {"name": [[...], ...]}
    mapping: "values": {"label": number}
JSON null means "no data" and becomes NaN.

Each loader is cached (lru_cache), so a table is read and validated once per
process. Arrays are made read-only so a cached table cannot be altered by
accident; the dataclasses are frozen so their fields cannot be reassigned.
"""

import json
from functools import lru_cache
from importlib.resources import files

import numpy as np

from concretecalc.tables.models import Grid2D, LabelMap, Series1D, TableMeta

_META_KEYS = ("id", "title", "source", "verified_against_primary", "units", "notes")


def _read_json(table_id: str) -> dict:
    """Read data/<table_id>.json from the installed package (works from a wheel or an editable install)."""
    path = files("concretecalc") / "data" / f"{table_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"no reference table named '{table_id}' in concretecalc/data")
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _check_kind(raw: dict, table_id: str, expected_kind: str) -> None:
    kind = raw.get("kind")
    if kind != expected_kind:
        raise ValueError(f"table '{table_id}' has kind {kind!r}, but this loader expects kind {expected_kind!r}")


def _build_meta(raw: dict, table_id: str) -> TableMeta:
    meta = raw.get("meta")
    if not isinstance(meta, dict):
        raise ValueError(f"table '{table_id}' has no 'meta' object")
    missing = [key for key in _META_KEYS if key not in meta]
    if missing:
        raise ValueError(f"table '{table_id}': meta is missing {missing}")
    if meta["id"] != table_id:
        raise ValueError(f"table file '{table_id}.json' declares meta.id {meta['id']!r}; they must match")
    return TableMeta(
        id=meta["id"],
        title=meta["title"],
        source=meta["source"],
        verified_against_primary=bool(meta["verified_against_primary"]),
        units=dict(meta["units"]),
        notes=meta["notes"],
    )


def _read_only_array(values: list) -> np.ndarray:
    """Convert a JSON list (possibly with nulls) to a read-only float array; null -> NaN."""
    array = np.array(values, dtype=float)
    array.flags.writeable = False
    return array


@lru_cache(maxsize=None)
def load_series(table_id: str) -> Series1D:
    """Load a "series" table: one numeric axis x and named columns."""
    raw = _read_json(table_id)
    _check_kind(raw, table_id, "series")
    meta = _build_meta(raw, table_id)
    columns = {}
    for name, values in raw["series"].items():
        columns[name] = _read_only_array(values)
    return Series1D(meta=meta, x=_read_only_array(raw["x"]), columns=columns)


@lru_cache(maxsize=None)
def load_grid(table_id: str) -> Grid2D:
    """Load a "grid2d" table: numeric axes rows and cols, and named 2-D variants (rows x cols)."""
    raw = _read_json(table_id)
    _check_kind(raw, table_id, "grid2d")
    meta = _build_meta(raw, table_id)
    variants = {}
    for name, values in raw["variants"].items():
        variants[name] = _read_only_array(values)
    return Grid2D(
        meta=meta,
        rows=_read_only_array(raw["rows"]),
        cols=_read_only_array(raw["cols"]),
        variants=variants,
    )


@lru_cache(maxsize=None)
def load_mapping(table_id: str) -> LabelMap:
    """Load a "mapping" table: label -> number (null -> NaN)."""
    raw = _read_json(table_id)
    _check_kind(raw, table_id, "mapping")
    meta = _build_meta(raw, table_id)
    values = {}
    for label, number in raw["values"].items():
        if number is None:
            values[label] = float("nan")
        else:
            values[label] = float(number)
    return LabelMap(meta=meta, values=values)


def list_table_ids() -> tuple[str, ...]:
    """Ids (file names without .json) of every table in concretecalc/data, sorted."""
    data_dir = files("concretecalc") / "data"
    ids = []
    for entry in data_dir.iterdir():
        if entry.name.endswith(".json"):
            ids.append(entry.name[: -len(".json")])
    return tuple(sorted(ids))
