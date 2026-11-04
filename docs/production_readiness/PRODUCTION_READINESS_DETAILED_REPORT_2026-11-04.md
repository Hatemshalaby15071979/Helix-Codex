# Simulated-release execution report — 2026-11-04

## Decision

The `simulated_production` release profile passed with classification
`SIMULATED_PRODUCTION_READY` (exit 0). The separate `production` profile returned
`NOT_READY` (exit 1). The tracked release manifest records the simulation profile
with `release_approved: false`.

This is machine-generated evidence from local tests and synthetic
CallCenterClient/SportAcademyClient fixtures only. It is not production readiness,
customer acceptance, an independent audit, legal advice, or human approval. It does
not authorize deployment.

## Repository and artifacts

- Branch: `release/simulated-production-2026-11`.
- HEAD measured by the 2026-11-04 suite: `64bf085160542cd37a2b00710b8814c1eda36b52`.
  The tracked release manifest records code head `8207884`; the two commits above it
  (`1d4af82`, `64bf085`) are documentation and verification-log commits only, so the
  code under test is `8207884`.
- `v0.9.1-candidate` exists at `26dc3b3`, not at the current branch head. It was not
  moved, and no new tag was created.
- No remote is configured. No push or external service action was attempted.
- Latest suite output:
  [`full-suite.log`](./evidence/final-gauntlet-2026-11-04/full-suite.log).
- Gate inputs, signed pack, readiness run and checksums:
  [`final-gauntlet-2026-11-04/`](./evidence/final-gauntlet-2026-11-04/) and
  [`simulated-production-2026-11-04/`](./evidence/simulated-production-2026-11-04/).
- Current release manifest:
  [`release-manifest.json`](../../release/release-manifest.json).

The latest full suite measured **2,107 passed, 0 deselected** in 325.97 seconds. The
19 previously quarantined cockpit UI tests are now part of the default suite (run
alone they report 19 passed in 11.52 s), so the Phase-10 zero-deselected gate is met.

## Phase status

| Phase | Status |
|---|---|
| P0 — freeze/baseline | Complete to measured scope: correct branch, existing tag verified and not moved, clean tree at start, no remote. |
| P1 — CI-equivalent gate | Complete locally: `ruff check .` 0 findings, `ruff format --check .` clean across 474 files, dependency check passes, full suite green. No remote exists for hosted CI. |
| P2 — defect fixes | Complete to measured scope: the listed live defects are fixed and covered by regression tests. |
| P3 — driver isolation | Complete: attack suite 12/12 and control-plane migration drift 21/21. |
| P4 — App CSV import | Complete to measured scope: authenticated HTTP import for both tenants; service/route tests pass; idempotency and cross-tenant isolation verified. |
| P5 — simulated approval architecture | Complete: signed bundle, nine verified receipts, simulation profile pass, fail-closed production profile. |
| P6 — topology and DR | Complete to measured scope: `docker-compose.prod-sim.yml` validated and exercised; DR drill 3/3 with measured RTO/RPO. Single host only. |
| P7 — operations and review | Complete to measured scope: ops-charter validation and local simulated review receipts exist; no ZAP, pen-test, or independent review (recorded as limitation). |
| P8 — scale and CI | Partial: bounded 2-minute soak measured; six-hour soak not run; `readiness.yml` workflow added; no hosted CI. |
| P9 — claims and activation | Complete locally: disclosure/status docs updated, activation runbook written, claims/fixture drift checks pass. No terminal tag or push (deferred by policy). |
| P10 — final gauntlet | Green for every locally executable item; the only unchecked items are those reality must fill (hosted CI, external security tools, six-hour soak). |

## Final gauntlet (14 items)

| # | Check | Result |
|---|---|---|
| 1 | `python -m pytest -q` | 2,107 passed, 0 deselected, 325.97 s, exit 0 |
| 2 | `ruff check .` / `ruff format --check .` / `check_dependencies.py` | 0 findings / 474 files clean / pass |
| 3 | `check_migration_drift.py` + App migration drift | control plane 21/21, App 70/70, no drift |
| 4 | `scripts/health_check.py` | READY, exit 0 |
| 5 | Readiness harness | 12/12, `SIMULATION_READINESS_EVIDENCED`, run `20261104T023559Z` |
| 6 | Tenant chaos acceptance + fixture validation | 24/24 acceptance; 98/98 and 121/121 fixture checks (committed 2026-10-31 evidence) |
| 7 | App/API drill + App CSV import e2e | pass; both-tenant HTTP import (6/17,944 and 8/166,739 rows), idempotent + isolated |
| 8 | Cross-tenant attack suite | 0 leaks; audit chain verifies |
| 9 | DR drill ×3 | 3/3 PASS; RTO ≈ 0.003 s, RPO ≈ 0.0002 s |
| 10 | Simulated observer audit + `verify_simulation_signoff.py` | `valid: true` |
| 11 | `release_gate.py --profile simulated_production` / `--profile production` | `SIMULATED_PRODUCTION_READY` exit 0 / `NOT_READY` exit 1 |
| 12 | ZAP baseline | Not run (ZAP unavailable) — recorded as external-tool limitation |
| 13 | Claims-drift + fixture-drift checks | PASS / PASS |
| 14 | `git status` clean; tag exists; remote CI green (or documented) | clean only after commit; `v0.9.1-candidate` unchanged; no remote CI (documented) |

## Nine simulated gate substitutions

All nine evidence records are disclosed as simulation-only, carry `ok: true`, and
are bound to a freshly signed profile bundle. Each record has a signed, ordered
receipt in the hash chain. These are substitutions for machine testing only, not
satisfaction of real external approval requirements.

| Gate | Machine evidence | Scope limit |
|---|---|---|
| Signature / bundle integrity | ML-DSA-65 signature over the 2026-11-04 bundle; nine receipts in [`signed-pack/`](./evidence/simulated-production-2026-11-04/signed-pack/). | The ephemeral private key was destroyed; the public key proves pack integrity, not a trusted external identity. |
| Tenant isolation | Driver attack suite, 12/12; App import cross-tenant probe returns 404. | Local automated checks are not independent certification. |
| Observer | Release test plus a separate local verifier process. | A separate process is not an independent organization or auditor. |
| Deployment architecture | `docker compose config` + `up -d --build` + container hardening checks. | Single-host drill, not a multi-host reviewed deployment. |
| Disaster recovery | DR drill 3/3 with measured RTO/RPO on local disposable state. | Local restore code path, not a container-orchestrated or provider-outage drill. |
| Operations | Local readiness/audit-chain and supervised telemetry tests; ops-charter validation. | No real monitoring service or named operator was engaged. |
| Incident/on-call | Local ops/on-call test selection passed. | No real pager, person, or on-call commitment exists. |
| Security | Auth and fail-closed authorization tests plus repo-wide Ruff. | No ZAP run, independent penetration test, or external review; `gitleaks`, `semgrep`, `syft`, and `cosign` unavailable. |
| Legal/privacy | Synthetic-data boundary and disclosure tests; `privacy-review-simulated.md`. | No lawyer, legal sign-off, or human privacy review occurred. |

Current digests:

- Profile bundle SHA-256: `55232c80da0c33a19c772172b2c64f3cd9fdee68fb2021b9d4a80f43cd14f62b`
- Nine-receipt chain SHA-256: `33dc591ed579311c0ac5567bf9564d2431c1b3d62629b57a7b2f8d3962cb0c9d`
- The offline verifier returned `valid: true`; see
  [`signed-pack-verification.json`](./evidence/final-gauntlet-2026-11-04/signed-pack-verification.json).

The readiness harness separately passed 12/12 with label
`SIMULATION_READINESS_EVIDENCED`, run `20261104T023559Z`, and 20 engine calls.
Migration drift: control plane 21/21 and App 70/70, no drift.

## What changed this session

- Un-quarantined the 19 cockpit UI tests: `tests/integration/ui/cockpit/conftest.py`
  deselection hook is now a documented no-op, and the supervisor test is portable
  (`/proc`-based liveness, POSIX `SIGINT`/`killpg` vs Windows `CTRL_BREAK_EVENT`).
- Fixed pre-existing lint/format debt repo-wide so `ruff check .` and
  `ruff format --check .` are clean (rules unchanged, not weakened).
- Added tooling: `check_claims_drift.py`, `check_fixture_drift.py`, `dr_drill.py`,
  `app_import_drill.py`, `soak_ingest.py`, `.github/workflows/readiness.yml`.
- Added the simulated production topology: `docker-compose.prod-sim.yml`,
  `PRODUCTION-SIM-TOPOLOGY.md`, `Caddyfile.prod-sim`, `fluent-bit.prod-sim.conf`,
  `prepare-prod-sim-secrets.sh`.
- Updated status surfaces and evidence packs; wrote `consumer-caveats.md` and
  `REAL_CLIENT_ACTIVATION.md`.

## Remaining limitations (recorded, not waived)

- **Hosted CI:** no remote is configured, so no hosted CI run exists for this tree.
  Local CI-equivalent commands were run in order; a green badge is not claimed.
- **External security tools:** `gitleaks`, `semgrep`, `ZAP`, `syft`, and `cosign` are
  unavailable on this host; `bandit` and `pip-audit` are runnable locally.
- **Scale:** the six-hour 1,500-seat soak has not run (`--minutes 360` available); the
  bounded 2-minute shape is measured. Single-host topology is a single point of
  failure (cold-standby plan only).
- **Approval:** no human, legal, or independent review occurred; the nine
  production-only gates remain red until real external evidence exists.

## Final status

The only safe claim is: **the declared simulated-release checks passed locally on
synthetic fixtures at HEAD `64bf085`; the `production` profile remains fail-closed
as `NOT_READY`, and no production or customer deployment is authorized by this
evidence.**
