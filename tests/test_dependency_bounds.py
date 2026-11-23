"""BLK-010 regression: the installed numeric stack must import together.

The project hard-pins ``numpy>=1.24,<2`` (dtype promotion rules would silently
change engine outputs). Streamlit pulls ``pyarrow``, which is not declared
upstream with a numpy bound; pyarrow >= 26 refuses NumPy 1.x at import time and
crashed every fresh checkout at ``st.dataframe`` (measured 2026-11-03).
``pyarrow>=25.0.1,<26`` is pinned (pip-audit fix for PYSEC-2026-113) in ``requirements.txt`` and the lock for this
reason. This test fails loudly if the installed set ever drifts apart again.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pyarrow_imports_with_installed_numpy() -> None:
    pyarrow = importlib.import_module("pyarrow")
    numpy = importlib.import_module("numpy")
    major = int(numpy.__version__.split(".")[0])
    assert major < 2, (
        "numpy>=2 is outside the project's hard bound; re-baseline every numeric engine first"
    )
    assert int(pyarrow.__version__.split(".")[0]) >= 25


def test_pyarrow_is_pinned_consistently() -> None:
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    lock = (REPO_ROOT / "release" / "requirements.lock.txt").read_text(encoding="utf-8")
    req_match = re.search(r"^pyarrow>=25\.0\.1,<26", requirements, re.MULTILINE)
    lock_match = re.search(r"^pyarrow==25\.0\.1$", lock, re.MULTILINE)
    assert req_match, "requirements.txt must bound pyarrow to >=25.0.1,<26"
    assert lock_match, "release/requirements.lock.txt must pin pyarrow==25.0.1"


def test_numpy_hard_bound_matches_lock() -> None:
    requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")
    lock = (REPO_ROOT / "release" / "requirements.lock.txt").read_text(encoding="utf-8")
    assert re.search(r"^numpy>=1\.24\.0,<2\.0\.0$", requirements, re.MULTILINE)
    assert re.search(r"^numpy==1\.26\.4$", lock, re.MULTILINE)


@pytest.mark.parametrize("module", ["pandas", "scipy", "sklearn"])
def test_numeric_stack_imports(module: str) -> None:
    importlib.import_module(module)
