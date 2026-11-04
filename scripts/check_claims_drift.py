#!/usr/bin/env python3
"""Fail when a current status surface makes a production claim it cannot prove.

This is deliberately narrow. Historical logs, dated evidence packs, changelogs and
ADRs are snapshots of what was measured at a point in time; rewriting them would be
dishonest in the other direction. The checker therefore inspects only the documents
that present *current* status, plus the tracked release manifest.

Rules, all heuristic but fail-closed for the wording this repository forbids:

* a positive production classification (``PRODUCTION_READY``, ``PRODUCTION_APPROVED``,
  ``production-ready``) must never appear;
* ``certified`` and ``audited by`` must not describe this project unless the line
  explicitly denies or scopes them to a simulation;
* a current surface that mentions ``SIMULATED_PRODUCTION_READY`` must also disclose
  that the result is a simulation and not a production classification;
* the tracked release manifest classification must be an allowed value.

Exit 0 = no drift, 1 = drift, 2 = a required surface is missing.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Current-status surfaces. Dated evidence, changelogs, ADRs and release notes are
# intentionally excluded: they record history, not the present claim.
CURRENT_SURFACES = (
    "README.md",
    "index.html",
    "docs/PRODUCTION_STATUS.md",
    "docs/release/release-boundary.md",
)

ALLOWED_CLASSIFICATIONS = {
    "NOT_READY",
    "CONTROLLED_PILOT_READY",
    "SIMULATED_PRODUCTION_READY",
}

SCOPING = re.compile(
    r"\b(not|no|never|none|without|simulat\w*|denied|forbid\w*|blocked|"
    r"requires?|required|red|pending|missing|gate|gates|remains)\b",
    re.IGNORECASE,
)

# A positive claim, in the forms the repository forbids. A match is tolerated when
# the same line scopes it (negation, simulation qualifier, or a blocker statement).
POSITIVE_CLAIMS = (
    re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE),
    re.compile(r"\bPRODUCTION_(READY|APPROVED|CERTIFIED)\b"),
    # "certified isolation" is a gate name in this repository; a claim looks like
    # "certified by <body>" or "certified for production".
    re.compile(r"\bcertified\s+(by|for|production)\b", re.IGNORECASE),
    re.compile(r"\baudited\s+by\b", re.IGNORECASE),
)

SIMULATION_TOKEN = re.compile(r"SIMULATED_PRODUCTION_READY")
SIMULATION_DISCLOSURE = re.compile(r"\b(simulation|simulated)\b", re.IGNORECASE)


def _iter_surfaces(extra: list[str]) -> list[pathlib.Path]:
    paths = [ROOT / name for name in CURRENT_SURFACES]
    paths.extend(ROOT / name for name in extra)
    return paths


def _scan_text(path: pathlib.Path) -> list[str]:
    problems: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return [f"{path.relative_to(ROOT)}: required status surface is missing"]

    for number, line in enumerate(text.splitlines(), start=1):
        for pattern in POSITIVE_CLAIMS:
            if not pattern.search(line):
                continue
            if SCOPING.search(line):
                continue
            problems.append(
                f"{path.relative_to(ROOT)}:{number}: unqualified claim "
                f"{pattern.pattern!r}: {line.strip()[:160]}"
            )

    if SIMULATION_TOKEN.search(text) and not SIMULATION_DISCLOSURE.search(text):
        problems.append(
            f"{path.relative_to(ROOT)}: names SIMULATED_PRODUCTION_READY without a "
            "simulation disclosure in the same document"
        )
    return problems


def _scan_manifest(path: pathlib.Path) -> list[str]:
    if not path.is_file():
        return [f"{path.relative_to(ROOT)}: release manifest is missing"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"{path.relative_to(ROOT)}: manifest is not valid JSON: {exc}"]
    classification = payload.get("classification")
    if classification not in ALLOWED_CLASSIFICATIONS:
        return [
            f"{path.relative_to(ROOT)}: classification {classification!r} is not one of "
            f"{sorted(ALLOWED_CLASSIFICATIONS)}"
        ]
    if classification == "SIMULATED_PRODUCTION_READY" and payload.get("release_approved"):
        # The simulation profile must never claim human release approval.
        return [f"{path.relative_to(ROOT)}: simulated classification claims release_approved"]
    return []


def check(extra: list[str] | None = None) -> list[str]:
    problems: list[str] = []
    for path in _iter_surfaces(extra or []):
        problems.extend(_scan_text(path))
    problems.extend(_scan_manifest(ROOT / "release" / "release-manifest.json"))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        help="additional repo-relative status surface to scan (repeatable)",
    )
    args = parser.parse_args(argv)
    problems = check(args.extra)
    if problems:
        print("CLAIMS_DRIFT: FAIL", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("CLAIMS_DRIFT: PASS (no unqualified production claim found)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
