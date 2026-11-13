# ME-12 — Owner Decision: Dependabot branches & oversized AGENTS.md

This document records the open decisions for ME-12. It makes **no changes** to
dependencies, branches, or `AGENTS.md` content — those are owner decisions.

## 1. Stale Dependabot branches (18 found, 0 open PRs)

`gh pr list --state open` shows **no open Dependabot PRs**. The bumps survive only
as archived/local branches:

### pip bumps (`archive/dependabot/pip/*`, mirrored on `origin/dependabot/pip/*`)
- contourpy-1.4.0
- coverage-7.17.1
- nodeenv-1.12.0
- numpy-2.5.4
- platformdirs-4.14.3
- plotly-7.1.0
- python-discovery-1.9.2
- sqlalchemy-2.1.8
- types-pyyaml-6.0.12.20261103
- watchdog-7.0.0

### github_actions bumps (`archive/dependabot/github_actions/*`)
- actions/checkout-7
- setup-python-7
- upload-artifact-7

### Owner decision A — what to do with them
- **Option 1 (recommended):** apply the version bumps to `requirements*.txt` /
  CI action versions directly (verify each version exists on PyPI/GitHub first),
  then delete the stale `archive/dependabot/*` branches and prune
  `origin/dependabot/*`. No history rewrite; just branch deletion.
- **Option 2:** delete the stale branches as-is (the bumps are already reflected
  elsewhere or no longer wanted).
- **Option 3:** keep them as an archived reference (current state).

Note: branch deletion is a shared-state action — only the owner should execute it.

## 2. Oversized AGENTS.md (5,776 lines / 354 KB)

`AGENTS.md` is a full build ledger (latest entry references 2,000 passed local
simulated suite). It is far larger than a typical agent-orientation file.

### Owner decision B — trimming strategy
- **Option 1 (recommended):** move the historical build-ledger sections
  (e.g. §27–§28 and dated status blocks) into `docs/` (e.g. `docs/build-ledger/`)
  and keep `AGENTS.md` as a concise index + current status (target < 400 lines).
- **Option 2:** split `AGENTS.md` into `AGENTS.md` (orientation) +
  `AGENTS.details.md` (reference), linked from the top.
- **Option 3:** leave as-is.

`docs/` also contains commercial/client material (`COMMERCIAL_STORY.md`,
`CASE_STUDY.md`, `HELIX_CODEX_APP_AGENT_PROMPTS.md`, etc.); confirm whether any
of that should be moved out of the public/private source tree per ME-16.

## Status
Draft — awaiting owner decisions A and B. No dependency, branch, or doc content
changes are performed by this PR.
