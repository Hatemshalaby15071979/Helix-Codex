# Release notes — Helix Prime

**Latest release tag recorded in this historical note:** `v1.1.0` — 2026-08-29
(`b077a918…`, "Integrate controlled-pilot deliverables, governance package, and test CI").
Prior tag: `v1.0.0` — 2026-08-27 (`681f0b28…`, "Fix cockpit launch, add setup.bat, relax
Python deps to 3.10+").

## Current status (2026-10-31)

- Local test suite: **2,000 passed, 19 deselected** (Python 3.12).
- Fixture/engine readiness: **12/12 gates**, 20 calls across six engines and two
  synthetic tenants, zero engine errors.
- App/API tenant and operations drill: passed; focused tests **128 passed**.
- Simulated design-partner drill: `PASS_SIMULATED`, **14/14 checks**. It used synthetic
  data and deterministic simulated reviewer checks, not real customer or independent
  review evidence.
- The production profile remains **`NOT_READY`**; nine production-only gates remain
  open. No real customer pilot, production deployment, external audit, or legal review
  is recorded.
- See [`PRODUCTION_STATUS.md`](PRODUCTION_STATUS.md) and
  [`production_readiness/simulated-design-partner-drill-2026-10-31.md`](production_readiness/simulated-design-partner-drill-2026-10-31.md)
  for current scope and boundaries.

The remainder of this document is the **2026-09-29 documentation-alignment snapshot**.
Its measurements, branch names, and open-item list are retained as history and must not
be read as the current status.

## What is in the current state

- **Governance core.** Fail-closed `evaluate_gate()` (`control_plane/governance.py:950`)
  with four hard-deny and three approval branches; role profiles from
  `organization/role-catalog.yaml`. Deny-by-default authorization, workflow state
  machine with approvals/retries/dead-letter, append-only hash-chained `audit_events`
  ledger.
- **One engine exercised end to end.** WFM (Erlang C) drives the governed demo through
  the gate (`helix_codex_app/integration/engine_bridge.py:529-587`).
- **Green CI (first time, 2026-09-29).** All 17 steps pass on run `36497766876`
  (`839507e`): **1,897 passed / 0 failed**, coverage **86.91%**, `ruff
  check` clean on 17 paths, `ruff format --check` clean (429 files), governance checker
  PASS, build OK (`AGENTS.md:39-44`, §21). Verified locally this session: `ruff check`
  exit 0, `ruff format --check` exit 0.
- **Two vertical capability packs.** `capabilities/restaurant/` (reference) and
  `capabilities/sports_academy/` (sports-academy prototype built with synthetic data;
  Scoach Academy Hub was a target scenario, not a confirmed partner).

## Validation gates (this session)

| Gate | Result | Source |
| --- | --- | --- |
| `ruff check` (17 CI paths) | **0 errors** (exit 0) | local run, 2026-09-29 |
| `ruff format --check .` | **Clean** — 429 files | local run, 2026-09-29 |
| Full test suite (repo CI, snapshot 2026-09-29) | **1,897 passed / 0 failed** | `README.md:131`; this session subset 122 passed |
| Coverage floor (80%) | **86.91%** | `README.md:132` (repo CI; not re-measured this session) |
| Release gate `production` | `NOT_READY` (exit 1) | `AGENTS.md:1451-1452` |

## Headline numbers (from `README.md` claims table / this run)

- CI, end to end: all 17 steps pass (run `36497766876`, `839507e`, 2026-09-29).
- Full test suite: 1,897 passed / 0 failed (repo CI, snapshot 2026-09-29); 19 quarantined UI tests deselected; this session re-ran a claims-relevant subset (122 passed).
- Coverage: 86.91% (server + connectors, 80% floor; repo CI).
- Six engines named; **all six** compute a real result end to end — CX's risk thresholds
  load from `config/risk_thresholds.yaml`; no adapter is scaffolding
  (`docs/KNOWN_ISSUES.md` issue 3).

## Does NOT show

- No real customer traffic, design partner, or pilot. Demo data is `simulated_realistic`
  by design.
- No proof that the engines compute correct results. All six adapters now return computed
  results (CX's risk thresholds load from `config/risk_thresholds.yaml`), but the suite
  asserts adapter contracts, not engine accuracy.
- No production deployment; nine production-only gates red (`AGENTS.md:1516-1519`).
- No external security audit, certified data isolation, or signed installer.
- The two CI container steps (16–17) are not reproducible on this machine (Docker not
  running); they rest on the remote green run (`AGENTS.md:5152-5153`).

## Open items as recorded in the 2026-09-29 snapshot — historical

- The engine scaffolding gap (issue 3) has since been closed; all six adapters compute
  on the 2026-10-31 synthetic readiness fixtures.
- Gate `oversight_only` and `requires_approval` defects (issues 1 and 2) were fixed.
- WFM Erlang C and CX configuration defects were subsequently fixed.
- Cockpit UI tier quarantined (19 tests).
- The 19-test cockpit UI quarantine remains reflected in the current test count.
