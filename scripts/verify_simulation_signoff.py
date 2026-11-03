#!/usr/bin/env python3
"""Verify a disclosed simulated release evidence pack offline."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from release import simulation  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "pack",
        nargs="?",
        type=pathlib.Path,
        default=simulation.simulation_evidence_dir(),
        help="simulation evidence directory (defaults to HELIX_SIMULATION_EVIDENCE_DIR)",
    )
    args = parser.parse_args(argv)
    valid, detail, manifest = simulation.verify_simulation_signoff(args.pack, ROOT)
    print(
        json.dumps(
            {
                "simulation": True,
                "disclosure": "SIMULATION ONLY; not external approval or certification.",
                "valid": valid,
                "detail": detail,
                "profile_bundle_sha256": (
                    manifest.get("profile_bundle_sha256") if manifest is not None else None
                ),
                "audit_receipts_sha256": (
                    manifest.get("audit_receipts_sha256") if manifest is not None else None
                ),
            },
            sort_keys=True,
        )
    )
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
