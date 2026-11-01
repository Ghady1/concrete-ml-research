"""Architecture rules (CLAUDE.md ground rule 1), enforced by static import scanning.

- Nothing under src/ may import streamlit or matplotlib (UI code stays in app/).
- Inside src/concretecalc, pandas / openpyxl may only be imported by
  calibration/dataset.py. (The owner's src/concrete_ml package is outside that
  second rule: ASSUMPTIONS A-07.)
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
ENGINE = SRC / "concretecalc"
UI_PACKAGES = {"streamlit", "matplotlib"}
DATAFRAME_PACKAGES = {"pandas", "openpyxl"}
PANDAS_ALLOWED = {ENGINE / "calibration" / "dataset.py"}


def imported_top_level_names(path: Path) -> set[str]:
    """Top-level package names imported anywhere in a file (import x.y / from x.y import z)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # level > 0 means a relative import (inside our own package).
            if node.module is not None and node.level == 0:
                names.add(node.module.split(".")[0])
    return names


def python_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.py"))


def test_there_are_files_to_scan():
    assert len(python_files(ENGINE)) >= 4


@pytest.mark.parametrize("path", python_files(SRC), ids=lambda p: str(p.relative_to(SRC)))
def test_no_ui_imports_under_src(path):
    bad = imported_top_level_names(path) & UI_PACKAGES
    assert bad == set(), f"{path} imports UI package(s) {bad}"


@pytest.mark.parametrize("path", python_files(ENGINE), ids=lambda p: str(p.relative_to(SRC)))
def test_pandas_only_in_calibration_dataset(path):
    if path in PANDAS_ALLOWED:
        return
    bad = imported_top_level_names(path) & DATAFRAME_PACKAGES
    assert bad == set(), f"{path} imports {bad}; only calibration/dataset.py may"


def test_scanner_detects_forbidden_imports(tmp_path):
    # Guard against a scanner that silently finds nothing.
    sample = tmp_path / "bad.py"
    sample.write_text("import matplotlib.pyplot as plt\nfrom streamlit import write\nimport pandas\n")
    assert imported_top_level_names(sample) == {"matplotlib", "streamlit", "pandas"}
