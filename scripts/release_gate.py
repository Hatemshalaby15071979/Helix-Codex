#!/usr/bin/env python3
"""
Helix Prime Codex C8 — single local release-gate command.

Usage:
    python3 scripts/release_gate.py [--profile PROFILE] [--soak COUNT] [--no-write-evidence]

Emits a deterministic classification:
    CONTROLLED_PILOT_READY, SIMULATED_PRODUCTION_READY, or NOT_READY.

The default profile is simulated_production. The production and
production_candidate profiles always return NOT_READY on this branch.

NOTE — by default this command is not a read-only check. It writes an evidence
pack and regenerates `release/release-manifest.json`, and that write records
`release_approved` from the `release_approval` gate, which reads the local pilot
consent flag for non-simulation profiles. A simulated run explicitly records no
human release approval. Running it against committed artifacts may therefore flip
`release_approved` from false to true. To inspect gate outcomes without touching
the committed manifest, pass `--no-write-evidence`.

Exit code 0 only when the emitted classification is a permitted C8 outcome.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from release.gate import main  # noqa: E402  (repo-root inserted above)

if __name__ == "__main__":
    sys.exit(main())
