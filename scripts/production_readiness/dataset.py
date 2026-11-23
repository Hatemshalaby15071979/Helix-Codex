"""Tenant fixture access for the production-readiness run.

The fixtures live outside this repository (they are client-shaped data, not
platform code). Resolution is explicit and fail-closed: an unresolvable root
raises :class:`TenantDatasetUnavailableError` instead of silently running on a
sample, because a readiness run that cannot name its input has proved nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import pandas as pd

CURATED_DIR = "16_DATA/curated"
CURATED_DIR_ENV = "HELIX_TENANT_CURATED_DIR"
RAW_DIR = "16_DATA/raw"
MANIFEST_REL = "21_MANIFEST/sha256sums.txt"
CARD_REL = "00_START_HERE/DATASET_CARD.md"
DISCLOSURE_TOKENS = ("synthetic", "no data was collected")
REAL_VIEW_MANIFEST = "_real_only_manifest.json"

TENANTS = ("callcenterclient", "sportacademyclient")


class TenantDatasetUnavailableError(RuntimeError):
    """The external tenant fixtures cannot be located or are incomplete."""


def _candidate_roots() -> List[pathlib.Path]:
    roots: List[pathlib.Path] = []
    env = os.environ.get("HELIX_TENANT_DATA_DIR")
    if env:
        roots.append(pathlib.Path(env))
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        roots.append(parent / "External tenant data")
    return roots


def tenant_data_root() -> pathlib.Path:
    """Return the directory holding both tenant fixtures."""
    for candidate in _candidate_roots():
        if all((candidate / name).is_dir() for name in TENANTS):
            return candidate
    raise TenantDatasetUnavailableError(
        "external tenant fixtures not found; set HELIX_TENANT_DATA_DIR to the "
        "directory containing callcenterclient/ and sportacademyclient/"
    )


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ManifestReport:
    """Outcome of checking the fixture against its own hash manifest."""

    listed: int
    missing: List[str] = field(default_factory=list)
    mismatched: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.mismatched


@dataclass(frozen=True)
class Tenant:
    """One external tenant fixture."""

    name: str
    root: pathlib.Path

    @property
    def curated_dir(self) -> pathlib.Path:
        override = os.environ.get(CURATED_DIR_ENV)
        return self.root / override if override else self.root / CURATED_DIR

    @property
    def raw_dir(self) -> pathlib.Path:
        return self.root / RAW_DIR

    def table_path(self, table: str) -> pathlib.Path:
        return self.curated_dir / f"{table}.csv"

    def available_tables(self) -> List[str]:
        if not self.curated_dir.is_dir():
            return []
        return sorted(path.stem for path in self.curated_dir.glob("*.csv"))

    @property
    def data_mode(self) -> str:
        """Declared mode of the *selected* curated tier, defaulting to synthetic.

        A real tier must say so explicitly in `_real_only_manifest.json`. An
        unreadable or contradictory declaration reports `invalid` so the gates
        fail closed rather than treating unknown data as a synthetic fixture.
        """
        path = self.curated_dir / REAL_VIEW_MANIFEST
        if not path.exists():
            return "synthetic"
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return "invalid"
        return str(document.get("data_mode", "invalid"))

    def real_view_report(self) -> Dict[str, object]:
        """Verify a declared real tier against its own manifest, fail-closed.

        Checks that the view actually declares `real`, that every declared table
        exists with the declared row count, and that the provenance register it
        names is present and matches its recorded digest. This substitutes for
        the synthetic fixture's table-count rule without weakening it: nothing
        here is inferred from an environment variable or from file presence.
        """
        problems: List[str] = []
        path = self.curated_dir / REAL_VIEW_MANIFEST
        if not path.exists():
            return {"declared": False, "mode": "synthetic", "problems": problems, "tables": {}}
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {
                "declared": True,
                "mode": "invalid",
                "problems": [f"unreadable real-view manifest: {type(exc).__name__}"],
                "tables": {},
            }

        if document.get("data_mode") != "real":
            problems.append(f"declared data_mode={document.get('data_mode')!r}, expected 'real'")

        actual_rows: Dict[str, int] = {}
        for entry in document.get("tables", []):
            table = str(entry.get("table", ""))
            expected = entry.get("rows")
            table_path = self.curated_dir / f"{table}.csv"
            if not table_path.exists():
                problems.append(f"declared table missing: {table}")
                continue
            with table_path.open("rb") as handle:
                rows = max(0, sum(1 for _ in handle) - 1)
            actual_rows[table] = rows
            if rows != expected:
                problems.append(f"{table}: {rows} rows, declared {expected}")

        register_rel = str(document.get("register", ""))
        register = self.root / register_rel if register_rel else None
        if register is None or not register.exists():
            problems.append("provenance register named by real view is missing")
        else:
            digest = sha256_file(register)
            if document.get("register_sha256") != digest:
                problems.append("provenance register digest does not match real view")

        return {
            "declared": True,
            "mode": document.get("data_mode"),
            "problems": problems,
            "tables": actual_rows,
            "total_rows": sum(actual_rows.values()),
        }

    def read_curated(
        self,
        table: str,
        columns: Optional[Iterable[str]] = None,
        *,
        as_text: bool = False,
    ) -> pd.DataFrame:
        path = self.table_path(table)
        if not path.exists():
            raise TenantDatasetUnavailableError(f"{self.name}: missing curated table {table}")
        if as_text:
            frame = pd.read_csv(
                path, dtype=str, keep_default_na=False, low_memory=False, usecols=columns
            )
        else:
            frame = pd.read_csv(path, low_memory=False, usecols=columns)
        if frame.empty:
            raise TenantDatasetUnavailableError(f"{self.name}: curated table {table} is empty")
        return frame

    def read_raw(self, name: str) -> pd.DataFrame:
        path = self.raw_dir / name
        if not path.exists():
            raise TenantDatasetUnavailableError(f"{self.name}: missing raw export {name}")
        return pd.read_csv(path, dtype=str, keep_default_na=False, low_memory=False)

    def raw_names(self) -> List[str]:
        if not self.raw_dir.is_dir():
            return []
        return sorted(path.name for path in self.raw_dir.glob("*.csv"))

    def manifest(self) -> Dict[str, str]:
        path = self.root / MANIFEST_REL
        if not path.exists():
            raise TenantDatasetUnavailableError(f"{self.name}: missing hash manifest")
        entries: Dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, _, relative = line.partition("  ")
            if relative:
                entries[relative] = digest
        return entries

    def verify_manifest(self) -> ManifestReport:
        listed = 0
        missing: List[str] = []
        mismatched: List[str] = []
        for relative, expected in self.manifest().items():
            listed += 1
            path = self.root / relative
            if not path.exists():
                missing.append(relative)
                continue
            if sha256_file(path) != expected:
                mismatched.append(relative)
        return ManifestReport(listed=listed, missing=missing, mismatched=mismatched)

    def disclosure_ok(self) -> bool:
        path = self.root / CARD_REL
        if not path.exists():
            return False
        text = path.read_text(encoding="utf-8").lower()
        return all(token in text for token in DISCLOSURE_TOKENS)

    def validate(self) -> None:
        """Fail closed if the fixture is structurally unusable."""
        report = self.verify_manifest()
        if not report.ok:
            raise TenantDatasetUnavailableError(
                f"{self.name}: manifest check failed "
                f"(missing={len(report.missing)}, mismatched={len(report.mismatched)})"
            )
        if not self.disclosure_ok():
            raise TenantDatasetUnavailableError(
                f"{self.name}: DATASET_CARD.md lacks the synthetic-data disclosure"
            )


def load_tenants(names: Iterable[str] = TENANTS) -> List[Tenant]:
    root = tenant_data_root()
    tenants: List[Tenant] = []
    for name in names:
        tenant = Tenant(name=name, root=root / name)
        tenant.validate()
        tenants.append(tenant)
    return tenants
