#!/usr/bin/env python3
"""Re-hash the synthetic tenant fixtures and report drift against a committed baseline.

The fixtures are too large to commit and live outside the repository, so their
integrity is pinned by the ``21_MANIFEST/sha256sums.txt`` file shipped with each
tenant. This script digests those manifests (and the curated file inventory) and
compares the result with ``docs/production_readiness/evidence/fixture-drift-baseline.json``.

Usage::

    python scripts/check_fixture_drift.py            # compare against the baseline
    python scripts/check_fixture_drift.py --write    # create/refresh the baseline

Exit 0 = match (or baseline written), 1 = drift, 2 = fixtures missing. A missing
fixture tree is *not* a pass: absence cannot demonstrate the hash is unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASELINE_REL = pathlib.Path("docs/production_readiness/evidence/fixture-drift-baseline.json")
TENANTS = ("callcenterclient", "sportacademyclient")
MANIFEST_REL = pathlib.Path("21_MANIFEST") / "sha256sums.txt"
CURATED_REL = pathlib.Path("16_DATA") / "curated"


def tenant_root() -> pathlib.Path:
    override = os.environ.get("HELIX_TENANT_DATA_DIR")
    if override:
        return pathlib.Path(override).expanduser().resolve()
    return (ROOT.parent.parent / "External tenant data").resolve()


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot(root: pathlib.Path) -> dict[str, object]:
    tenants: dict[str, object] = {}
    for tenant in TENANTS:
        base = root / tenant
        manifest = base / MANIFEST_REL
        curated = base / CURATED_REL
        if not manifest.is_file():
            raise FileNotFoundError(f"{tenant}: missing {MANIFEST_REL}")
        if not curated.is_dir():
            raise FileNotFoundError(f"{tenant}: missing {CURATED_REL}")
        curated_files = sorted(path.name for path in curated.glob("*.csv"))
        tenants[tenant] = {
            "manifest_sha256": _sha256(manifest),
            "manifest_bytes": manifest.stat().st_size,
            "curated_count": len(curated_files),
            "curated_files": curated_files,
        }
    return {"tenant_data_root": str(root), "tenants": tenants}


def snapshot_curated(root: pathlib.Path) -> dict[str, object]:
    """Hash every curated CSV so an in-place edit (same names) is still visible."""
    result: dict[str, object] = {}
    for tenant in TENANTS:
        curated = root / tenant / CURATED_REL
        result[tenant] = {
            name: _sha256(curated / name) for name in sorted(p.name for p in curated.glob("*.csv"))
        }
    return result


def build(root: pathlib.Path) -> dict[str, object]:
    return {"snapshot": snapshot(root), "curated_hashes": snapshot_curated(root)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--write", action="store_true", help="write the baseline instead of checking"
    )
    args = parser.parse_args(argv)

    root = tenant_root()
    try:
        payload = build(root)
    except FileNotFoundError as exc:
        print(f"FIXTURE_DRIFT: UNAVAILABLE ({exc})", file=sys.stderr)
        return 2

    baseline_path = ROOT / BASELINE_REL
    if args.write:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"FIXTURE_DRIFT: baseline written to {BASELINE_REL}")
        return 0

    if not baseline_path.is_file():
        print(
            f"FIXTURE_DRIFT: FAIL (no baseline at {BASELINE_REL}; run with --write)",
            file=sys.stderr,
        )
        return 1
    expected = json.loads(baseline_path.read_text(encoding="utf-8"))
    if expected != payload:
        print("FIXTURE_DRIFT: FAIL (fixture hashes differ from the committed baseline)")
        for tenant in TENANTS:
            old = expected.get("snapshot", {}).get("tenants", {}).get(tenant, {})
            new = payload["snapshot"]["tenants"][tenant]
            if old != new:
                print(f"  - {tenant}: snapshot changed")
            old_curated = expected.get("curated_hashes", {}).get(tenant, {})
            new_curated = payload["curated_hashes"][tenant]
            changed = sorted(
                name
                for name in set(old_curated) | set(new_curated)
                if old_curated.get(name) != new_curated.get(name)
            )
            if changed:
                print(f"  - {tenant}: curated files changed: {', '.join(changed[:10])}")
        return 1
    print("FIXTURE_DRIFT: PASS (fixture hashes match the committed baseline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
