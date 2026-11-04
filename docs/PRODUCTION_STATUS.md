# Helix Prime — current release and verification status

**Status measured:** 2026-11-04
**Release classification:** `SIMULATED_PRODUCTION_READY` in the local
`simulated_production` profile (synthetic fixtures, machine evidence);
`NOT_READY` for `production`.
**Deployment position:** not authorized for first-customer or production deployment.
**Disclosure:** simulation only. No human, legal, independent, or hosted-CI approval
is claimed. See [`SIMULATION_DISCLOSURE.md`](../SIMULATION_DISCLOSURE.md).

This page is the concise current-status summary. Dated logs and evidence packs are
historical snapshots and remain unchanged. The latest measured section is
[2026-11-04](#latest-measurement--2026-11-04); the 2026-10-31 and 2026-11-03 text
below is kept as history. The detailed implementation ledger is [`AGENTS.md`](../AGENTS.md);
the production boundary is [`release-boundary.md`](release/release-boundary.md).
The broader documentation map is [`DOCUMENTATION_STATUS.md`](DOCUMENTATION_STATUS.md).

> **Historical snapshots follow.** The sections from "What was verified" down to the
> "2026-11-03" measurement are dated records and are kept unchanged. The current
> state is the [2026-11-04](#latest-measurement--2026-11-04) section at the bottom of
> this page.

## What was verified

- **Full test suite:** 2,000 passed, 19 deselected, on the workspace Python 3.12
  environment. The 19 deselected tests belong to the separately quarantined cockpit
  UI tier; this result does not include that tier.
- **Tenant fidelity:** all 24 declared CallCenterClient and SportAcademyClient chaos
  acceptance checks passed. Fixture validation reported 98/98 and 121/121 checks;
  regenerating the overlays left 36 generated artifacts byte-identical.
- **Engine readiness:** the fresh synthetic-fixture pack passed 12/12 gates and made
  20 calls across WFM, RTA, CX, B2B, Personnel and CRM, for both tenants, with zero
  errors. Results are disclosed as sample data and are not measurements about real
  organizations. Evidence: [`2026-10-31-final/`](production_readiness/evidence/2026-10-31-final/).
- **App/API tenant and operations drill:** authenticated tenant-scoped HTTP workflows,
  cross-tenant denials, persistence across restart, backup verification, staged
  restore, migration checks and rollback passed. The focused set reported 128 passing
  tests. Evidence: [`app-tenant-ops-drill-2026-10-31.md`](release/app-tenant-ops-drill-2026-10-31.md).
- **Simulated design-partner drill:** `PASS_SIMULATED`, 14/14 combined checks. It
  processed the synthetic fixtures through the existing readiness harness, then used
  the real local App HTTP routes for tenant-scoped incident summaries and action tasks.
  The simulated reviewer checks are deterministic assertions, not separate LLM
  opinions, an independent audit, or legal advice. The App has no CSV upload endpoint;
  raw fixture ingestion was not performed through the App. See
  [`simulated-design-partner-drill-2026-10-31.md`](production_readiness/simulated-design-partner-drill-2026-10-31.md).
- **Changed-path code checks:** Ruff lint and format checks passed for the changed
  readiness/simulation paths. Repository-wide Ruff still reports 21 existing findings
  and 346 files needing formatting; that debt is not a clean full-repository result.

## What these results establish

They establish that the exercised local paths worked against documented synthetic
fixtures and disposable local deployments under the stated test conditions. The App
HTTP drill demonstrates tenant-scoped behavior for its tested routes; it is not an
independent certification or a production-scale isolation audit. The synthetic review
personas test explicit controls; they do not supply independent human authority.

The local `CONTROLLED_PILOT_READY` result is a gate classification based on this
repository's configured pilot scope. Its approval is internally generated and does
not mean that a real design partner participated or that a customer pilot occurred.
No live customer data, real customer traffic, or production service was used.

## Production blockers

The `production` profile remains fail-closed as `NOT_READY`. The nine production-only
gates still require evidence or authority outside this local simulation:

1. `signed_production_evidence`
2. `certified_data_isolation`
3. `external_observer_audit`
4. `production_deployment_architecture`
5. `disaster_recovery_evidence`
6. `operational_ownership`
7. `incident_oncall_ownership`
8. `security_review`
9. `legal_privacy_review`

An AI agent can help prepare test protocols, collect local evidence, check artifacts,
and rehearse operational procedures. It cannot turn a simulated review into an
independent audit, certification, legal review, production signature, or named human
on-call commitment. Those distinctions are part of the honest release boundary, not a
claim that local simulations are useless.

## Product and data boundaries

- Both tenant datasets are synthetic, client-shaped fixtures. Every derived result
  remains explicitly sample-labelled.
- The raw CSV exports are processed by the production-readiness harness, not uploaded
  through the App. The App supports authenticated document/task HTTP workflows; a
  tenant-scoped CSV import workflow is not implemented.
- No live external connector writes are enabled; no customer data leaves the local
  simulation.
- The engine readiness gates test measured fixture-level behavior, authorization,
  disclosure, determinism and latency. They do not independently certify all engine
  outputs as correct for real-world client operations.
- No real Scoach Academy Hub pilot or any other client deployment is recorded.
- No current remote CI result is asserted for the 2026-10-31 local source. The last
  recorded remote CI measurements are dated historical evidence in
  [`README.md`](../README.md) and [`AGENTS.md`](../AGENTS.md).

## Current next actions

1. Keep the nine production gates red until the corresponding external evidence and
   human authority genuinely exist.
2. If raw-file workflows are in scope, implement and test a tenant-scoped App import
   path; do not describe the current App HTTP drill as CSV ingestion.
3. Resolve the repository-wide lint/format debt and run the complete CI-equivalent
   validation against the exact release candidate before any release decision.
4. Preserve synthetic-data disclosure and the separation between simulated evidence
   and real customer, independent-review, or production evidence.

## Latest measurement — 2026-11-03

This section supersedes the earlier snapshot above as the latest local measurement;
the 2026-10-31 details remain historical. The simulated release gate returned
`SIMULATED_PRODUCTION_READY` (exit 0), while the separate `production` profile
returned `NOT_READY` (exit 1). The committed release manifest has
`release_approved: false`. This is not authorization for a customer or production
deployment.

- Full suite: **2,088 passed, 19 deselected**. The 19 deselected tests remain open;
  the ten-phase execution is incomplete.
- Readiness harness: 12/12 with label `SIMULATION_READINESS_EVIDENCED`; 20 engine
  calls using synthetic fixtures.
- Driver isolation: 12/12; migration drift: control plane 21/21 and App 70/70.
- Nine simulation gate receipts: ML-DSA-65 signature, ordered hash chain, and
  offline verification passed. The receipts prove pack integrity, not an external
  identity or independent review.
- No real client, external legal review, remote CI, or external service was used.
  The existing `v0.9.1-candidate` tag was not moved; no terminal tag was created.
  No remote is configured, so no push occurred.
- A transient local CLI classification incident and its correction are documented
  in the [detailed execution report](production_readiness/PRODUCTION_READINESS_DETAILED_REPORT_2026-11-03.md).

Full phase status, blocker limits and evidence links are in the
[2026-11-03 execution report](production_readiness/PRODUCTION_READINESS_DETAILED_REPORT_2026-11-03.md)
and the
[evidence pack](production_readiness/evidence/simulated-production-2026-11-03/).

## Latest measurement — 2026-11-04

This section supersedes the 2026-10-31 and 2026-11-03 snapshots above as the current
local measurement. The simulated release gate returned `SIMULATED_PRODUCTION_READY`
(exit 0) and the separate `production` profile returned `NOT_READY` (exit 1). This is
a simulation result on synthetic fixtures only; it is not authorization for a
customer or production deployment.

- **Full suite:** **2,107 passed, 0 deselected** in 325.97 s. The previously
  quarantined cockpit UI tier is un-quarantined and part of the default suite; run
  alone it reports 19 passed in 11.52 s.
- **Lint/format:** `ruff check .` exit 0 (0 findings) and `ruff format --check .`
  clean across 474 files; `scripts/check_dependencies.py` passes. The repository-wide
  lint/format debt listed as a "next action" in the historical section above is
  resolved.
- **Readiness harness:** 12/12 with label `SIMULATION_READINESS_EVIDENCED`
  (run `20261104T023559Z`); 20 engine calls on synthetic fixtures.
- **App CSV import drill:** authenticated HTTP import for both tenants —
  `callcenterclient` 6 tables / 17,944 rows and `sportacademyclient` 8 tables /
  166,739 rows, 0 failed; idempotent re-import and cross-tenant isolation verified.
  Curated CSVs without a declared schema (33 and 32 respectively) are skipped by
  design, not an error.
- **Disaster-recovery drill:** 3/3 PASS (backup → destroy → restore → verify); RTO
  ≈ 0.003 s and RPO ≈ 0.0002 s on local disposable state; audit chain verified each
  run.
- **Bounded ingest soak:** 1,500-seat shape, 2 min at 5 ticks/s — 600/600 accepted,
  0 dropped, p95 2.83 ms, RSS growth ratio 1.001, healthy after. The six-hour shape
  (`--minutes 360`) has **not** been run.
- **Simulated production topology:** `docker-compose.prod-sim.yml` parses
  (`docker compose config` exit 0); all three containers reach `healthy`; HTTPS
  `/readyz` 200 through Caddy (internal CA); security headers present; read-only
  roots, `cap_drop: [ALL]`, and non-root uid verified; logs delivered to the local
  sink; `down -v` removed all disposable volumes.
- **Gates:** `release_gate.py --profile simulated_production` →
  `SIMULATED_PRODUCTION_READY` (exit 0); `--profile production` → `NOT_READY`
  (exit 1, nine production-only gates red by design).
- **Signed simulation pack:** nine simulation receipts and the ordered hash chain
  verified offline (`valid: true`); this proves pack integrity, not an external
  identity or independent review.
- **Claims and fixture drift:** `check_claims_drift.py` PASS; `check_fixture_drift.py`
  PASS against the committed baseline.

### Remaining limitations (recorded, not waived)

- **Hosted CI:** no remote is configured, so no hosted CI run exists for this tree;
  the local CI-equivalent commands were run in order but no green badge is claimed.
- **External security tools:** `gitleaks`, `semgrep`, `ZAP`, `syft`, and `cosign` are
  unavailable on this host; `bandit` and `pip-audit` are runnable locally. No
  external scan result is claimed.
- **Scale:** the six-hour 1,500-seat soak has not run; only the bounded 2-minute
  shape is measured. The topology is a single host (single point of failure) with a
  cold-standby plan only.
- **Approval:** no human, legal, or independent review occurred; the nine
  production-only gates remain red until real external evidence exists.

The full 14-item gauntlet record is in
[`evidence/final-gauntlet-2026-11-04/`](production_readiness/evidence/final-gauntlet-2026-11-04/);
the phase status and limitations are in the
[2026-11-04 execution report](production_readiness/PRODUCTION_READINESS_DETAILED_REPORT_2026-11-04.md);
the activation path is [`REAL_CLIENT_ACTIVATION.md`](release/REAL_CLIENT_ACTIVATION.md).
