#!/usr/bin/env python3
"""Create a locally signed simulation evidence pack from machine-check records."""

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
    parser.add_argument("--evidence-json", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    evidence = json.loads(args.evidence_json.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        parser.error("evidence JSON must contain a gate-name mapping")
    manifest = simulation.create_simulation_signoff(ROOT, args.output, evidence)
    print(
        json.dumps(
            {
                "simulation": True,
                "disclosure": manifest["disclosure"],
                "output": str(args.output.resolve()),
                "profile_bundle_sha256": manifest["profile_bundle_sha256"],
                "audit_receipts_sha256": manifest["audit_receipts_sha256"],
                "gates": len(manifest["gates"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
