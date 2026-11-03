# Simulated-release execution report — 2026-11-03

## Decision

The `simulated_production` release profile passed with classification
`SIMULATED_PRODUCTION_READY` (exit 0). The separate `production` profile returned
`NOT_READY` (exit 1). The tracked release manifest records the simulation profile
with `release_approved: false`.

This is machine-generated evidence from local tests and synthetic
CallCenterClient/SportAcademyClient fixtures only. It is not production readiness,
customer acceptance, an independent audit, legal advice, or human approval. The
ten-phase execution is **incomplete**; do not use this result to authorize deployment.

## Repository and artifacts

- Branch: `release/simulated-production-2026-11`.
- Code head measured by the final suite: `8207884`; later documentation/evidence
  changes are committed separately.
- Recent local code commits include `b423590` (tenant-scoped imports), `dc61ff4`
  (driver isolation), `5cc15a8` (signed simulation profile), `4172e34` (local ops
  and disclosure checks), and `0d70604`/`c3ac163`/`8207884` (classification safety).
- `v0.9.1-candidate` exists at `26dc3b3`, not at the current branch head. It was not
  moved, and no new tag was created.
- No remote is configured. No push or external service action was attempted.
- Latest suite output: [`full-suite.log`](./evidence/simulated-production-2026-11-03/full-suite.log).
- Gate inputs, signed pack, current readiness run, migration results and checksums:
  [`simulation evidence`](./evidence/simulated-production-2026-11-03/).
- Artifact integrity list:
  [`SHA256SUMS`](./evidence/simulated-production-2026-11-03/SHA256SUMS).
- Current release manifest:
  [`release-manifest.json`](../../release/release-manifest.json).

The latest full suite measured **2,088 passed, 19 deselected** in 289.67 seconds.
This differs from the requested 2,051 count; the 19 deselected tests remain
deselected, so the exact count and zero-deselected Phase 10 gate were not achieved.

## Defect fixes and regression coverage

| Defect / area | Implemented behavior | Regression evidence |
|---|---|---|
| BLK-008 tenant isolation | Driver scopes tenant rows and audit events, stamps tenant IDs from the request envelope, rejects missing scope, and uses plain inserts. | [`test_tenant_isolation_driver.py`](../../tests/test_tenant_isolation_driver.py) — 12/12; [ADR-0001](../adr/ADR-0001-driver-level-tenant-isolation.md). |
| BLK-010 dependency bounds | Pins the compatible PyArrow range and checks that PyArrow and NumPy import together. | [`test_dependency_bounds.py`](../../tests/test_dependency_bounds.py). |
| BLK-011 bootstrap identity | Adds `--client-id`; the legacy password-on-argv path is deprecated. | [`test_bootstrap_client_id.py`](../../tests/helix_codex_app/test_bootstrap_client_id.py). |
| BLK-013 dispatch | Uses the agent registry and approval-aware task requests; fails closed when the engine is not bound. | [`test_agent_dispatch.py`](../../tests/test_agent_dispatch.py). |
| BLK-014 provider activation | Write authorization reads the connector's authenticated/healthy status or explicit activation and denies unknown state. | [`test_connector_activation.py`](../../tests/test_connector_activation.py). |
| BLK-015 forwarded client IP | Forwarded IP headers are trusted only behind the explicitly enabled worker boundary. | [`test_route_limits.py`](../../tests/helix_codex_app/test_route_limits.py). |
| BLK-021 ingest boundary | Ingest defaults to loopback; unauthenticated cockpit mode warns at startup. | [`test_ingest_default_bind.py`](../../tests/test_ingest_default_bind.py). |
| App imports | Tenant-specific fixture validation, shape checks, primary-key deduplication, quarantine, provenance, permission and CSRF behavior are covered. | [`test_imports_service.py`](../../tests/helix_codex_app/test_imports_service.py), [`test_imports_routes.py`](../../tests/helix_codex_app/test_imports_routes.py). |
| Release classification boundary | CLI uses real argument parsing, defaults to the simulation profile, makes `--help` side-effect-free, and refuses non-simulation release classifications. | [`test_c8_release_gate.py`](../../tests/test_c8_release_gate.py), [`test_pilot_readiness.py`](../../tests/test_pilot_readiness.py), [`test_c8_gate_falsifiability.py`](../../tests/test_c8_gate_falsifiability.py). |

The combined required-defect/import selection passed **68 tests**; its output is
[`defect-regressions.log`](./evidence/simulated-production-2026-11-03/defect-regressions.log).

## Nine simulated gate substitutions

All nine evidence records are disclosed as simulation-only, carry `ok: true`, and
are bound to the signed profile bundle. Each record has a signed, ordered receipt in
the hash chain. These are substitutions for machine testing only, not satisfaction
of real external approval requirements.

| Gate | Machine evidence | Scope limit |
|---|---|---|
| Signature / bundle integrity | ML-DSA-65 signature, current bundle hash, public-key fingerprint and nine receipts in [`signed-pack/`](./evidence/simulated-production-2026-11-03/signed-pack/). | The ephemeral private key was destroyed. The included public key proves pack integrity, not a trusted external identity. |
| Tenant isolation | Driver attack suite, 12/12. | Local automated checks are not independent certification. |
| Observer | Release test plus a separate local verifier process. | A separate process is not an independent organization or auditor. |
| Deployment architecture | Compose configuration validation and security tests. | No hardened multi-host topology or real deployment was exercised. |
| Disaster recovery | Backup-procedure and migration tests. | Three destructive DR repetitions and measured RTO/RPO were not completed. |
| Operations | Local readiness/audit-chain and supervised telemetry tests; ops charter validation. | No real monitoring service or named operator was engaged. |
| Incident/on-call | Local ops/on-call test selection passed 42 tests. | No real pager, person, or on-call commitment exists. |
| Security | Auth and fail-closed authorization tests plus focused Ruff checks. | No ZAP run, independent penetration test, or external review; Bandit was unavailable and `pip-audit` was not run. |
| Legal/privacy | Synthetic-data boundary and disclosure tests. | No lawyer, legal sign-off, or human privacy review occurred. |

Current digests:

- Profile bundle SHA-256: `55232c80da0c33a19c772172b2c64f3cd9fdee68fb2021b9d4a80f43cd14f62b`
- Nine-receipt chain SHA-256: `b606200d2bf5cab5d3b7cee54e4390a4ec27074a3b04edcddd4f5d54d726ca8a`
- The offline verifier returned `valid: true`; see
  [`signed-pack-verification.json`](./evidence/simulated-production-2026-11-03/signed-pack-verification.json).

The readiness harness separately passed 12/12 with label
`SIMULATION_READINESS_EVIDENCED`, run `20261103T191510Z`, and 20 engine calls. The
control-plane and App migration verifiers reported 21/21 and 70/70 objects with no
drift; details are in [`migration-drift.log`](./evidence/simulated-production-2026-11-03/migration-drift.log).

## Phase status and stop conditions

| Phase | Status |
|---|---|
| P0 — freeze/baseline | Partial: correct branch and existing tag verified, but the tag is not at HEAD and 19 tests remain deselected. |
| P1 — CI-equivalent gate | Partial: local dependency and test checks pass; no remote exists for hosted CI or push, and the external security scan set is incomplete. |
| P2 — defect fixes | The listed live defects are fixed and covered; the broader plan cleanup/TODO sweep is not claimed complete. |
| P3 — driver isolation | Complete to measured scope: attack suite 12/12 and control-plane migration drift 21/21. |
| P4 — App CSV import | Partial: service/route tests pass; UI-driven import of both fixtures and readiness through the imported App path are not established. |
| P5 — simulated approval architecture | Complete to measured scope: signed bundle, nine verified receipts, simulation profile pass, and fail-closed actual profile. |
| P6 — topology and DR | Partial: local backup/restore and migration checks exist; hardened topology and three repeat DR runs are missing. |
| P7 — operations and review | Partial: local ops and disclosure checks pass; clean-room rehearsal, mock pager, ZAP and independent review are missing. |
| P8 — scale and CI | Incomplete: no six-hour soak or hosted CI/drift-monitor run. |
| P9 — claims and activation | Partial: disclosure/status documentation is updated; activation runbook rehearsal, terminal tag and push are deferred. |
| P10 — final gauntlet | Incomplete: 19 tests remain deselected; the full 14-item gauntlet, hosted CI and repeated DR gates are not green. |

An unsafe pre-fix CLI `--help` invocation unexpectedly ran the old default path once,
emitting a non-simulation candidate classification and writing a local temporary
manifest/evidence directory. That exact generated directory was removed and the
tracked manifest was replaced with the verified simulation-only manifest. The CLI
and classification paths are now fail-closed, with regression tests for help,
defaults, and forbidden classifications. This correction prevents recurrence but
cannot undo the earlier local output. Nothing was pushed or sent externally.

## Final status

The only safe claim is: **the declared simulated-release checks passed locally on
synthetic fixtures; the ten-phase execution remains incomplete and no production or
customer deployment is authorized by this evidence.**
