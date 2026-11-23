#!/usr/bin/env python3
"""ME-15 guard: every agent-instruction file must carry the quarantine header.

Agent-directive files (prompts, constitutions, agent instructions) are *data, not
instructions*. They must contain the UNTRUSTED AGENT TEXT (ME-15) marker so an
automated agent does not treat their contents as commands to act on. This fails
the build if a matching file is missing the marker, so a new agent-instruction
file cannot be introduced without being explicitly quarantined.
"""

import glob
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = "UNTRUSTED AGENT TEXT (ME-15)"

# Known agent-instruction files (relative to repo root).
KNOWN = [
    "AGENTS.md",
    "docs/HELIX_CODEX_APP_AGENT_PROMPTS.md",
    "docs/audits/2026-09-10_agent_prompt_sequence.md",
    "docs/production_readiness/AUTONOMOUS_EXECUTION_PROMPT_2026-11-03.md",
    ".github/copilot-instructions.md",
]

# Glob patterns that should also be in scope for future agent-instruction files.
PATTERNS = [
    "AGENTS*.md",
    "docs/**/*_PROMPT*.md",
    "docs/**/*_prompt_sequence*.md",
    ".github/copilot-instructions.md",
]


def candidate_files():
    files = set()
    for rel in KNOWN:
        path = os.path.join(REPO_ROOT, rel)
        if os.path.isfile(path):
            files.add(path)
    for pat in PATTERNS:
        for path in glob.glob(os.path.join(REPO_ROOT, pat), recursive=True):
            if os.path.isfile(path):
                files.add(path)
    return files


def main():
    missing = []
    for path in sorted(candidate_files()):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4096)
        if MARKER not in head:
            missing.append(os.path.relpath(path, REPO_ROOT))
    if missing:
        sys.stderr.write(
            "ME-15: agent-instruction files missing the quarantine header "
            f"({MARKER}):\n  - " + "\n  - ".join(missing) + "\n"
        )
        return 1
    print("ME-15: all agent-instruction files carry the quarantine header.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
