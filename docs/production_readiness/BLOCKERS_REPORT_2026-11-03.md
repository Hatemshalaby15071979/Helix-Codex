# Helix Codex OS — Blockers Report (2026-11-03)

**Author:** OpenCode agent, commissioned by the project owner
**Scope:** Helix Codex App (`helix_codex_app/`) + Helix Prime dashboard/cockpit (`cockpit_ui.py`, Streamlit :8501, `ingest_engine.py` :8000) and the parent project (Helix Codex OS: six engines, nine agents, control plane, release gate)
**Data under test:** `External tenant data/callcenterclient` (198 MB) and `External tenant data/sportacademyclient` (106 MB) — synthetic, client-shaped fixtures; `simulated_realistic` provenance everywhere
**Method:** read the repo's own readiness/audit/release docs; re-ran the readiness harness on 2026-11-03; booted and exercised both apps live; measured lint/format; inventoried open known issues; inspected the release boundary and gates

> **Honesty boundary.** Everything below distinguishes three things: (1) measured on this machine on 2026-11-03; (2) recorded by the repo as measured on an earlier date; (3) not verifiable here at all. Nothing in this report claims a real client, a real external audit, a real legal review, or a real production deployment ever occurred. Where the plan (see companion file) closes a human/external gate, it does so by **simulation with mandatory disclosure**, never by fabricating authority.

---

## 0. What was verified live on 2026-11-03 (baseline)

| Check | Result | Evidence |
|---|---|---|
| Readiness harness re-run (`scripts/production_readiness/run.py`) | **12/12 gates PASS**, 20 engine calls, label `PRODUCTION_READINESS_EVIDENCED`, run `20261103T152704Z` | `/tmp/opencode/readiness-rerun-2026-11-03/` (out of repo) |
| Fixture integrity (both tenants) | PASS (PR-G01); raw-layer defects detected & cleaned (PR-G02); determinism (PR-G11); latency < 5000 ms (PR-G12) | same pack |
| App boot from clean env, healthz | HTTP 200 in ~4 s | `http://127.0.0.1:8100/app/healthz` |
| App fail-closed auth | `/app` without session → HTTP 401 `{"code":"auth_failed"}`; login `demo/owner` → 303 → `/app/` | browser session 2026-11-03 |
| App cockpit pack compute | Renders sports-academy owner board (38 active athletes, $7,960 MRR, 81% attendance, 7 at-risk, 67% utilisation), labelled `simulated_realistic` | `/app/cockpit` screenshot 2026-11-03 |
| Ops twin → ingest → cockpit | 120/120 ticks delivered, 0 dropped, spike at tick 40 produced an SLA-breach intervention (`sla_breach:44.06%<50.0%`, "Open voluntary overtime · moderate", $8,083 exposure avoided) visible in dashboard | `supervisor2.log`, `http://127.0.0.1:8501` screenshot 2026-11-03 |
| Focused API/App tenant & ops drill suite | **128 passed** | pytest 2026-11-03 |
| Ruff (repo-wide) | **20 errors, all under `marketing/helix-codex-deck/video/`** (S603/S310/F401/I001/B007/B023/B905); product code clean | measured 2026-11-03 |
| Ruff format (repo-wide) | 2 files would reformat (`scripts/production_readiness/payloads.py`, `tests/test_cx_risk_level_direction.py`); 446 already formatted | measured 2026-11-03 |
| Git worktree | **62 changed paths (57 modified, 5 untracked), uncommitted**, incl. identity-scrub docs + readiness fixes + drill evidence | `git status` 2026-11-03 |
| Local pyarrow/numpy conflict | **Cockpit crashed** (`ImportError: pyarrow requires NumPy 2.0 or newer, found 1.26.4`); fixed locally by `pyarrow==18.1.0`; **not yet pinned in `requirements.txt`/lock** | see BLK-010 |
| Fresh-install cockpit dead-end | Bootstrap created domain without `client_id` → cockpit rendered "no pack data can be scoped"; fixed in `helix_codex_app/scripts/bootstrap_owner.py` (`--client-id`, default = domain); demo DB patched | see BLK-011 |

The repo's own recorded state (not re-measured tonight, quoted as recorded): full suite **2,000 passed / 19 deselected (quarantined UI tier)** on Python 3.12 (2026-10-31); tenant chaos acceptance **24/24**; fixture validation **98/98** and **121/121**; simulated design-partner drill **14/14 PASS_SIMULATED**; App/API tenant-ops drill **128 passed**; release gates: `controlled_pilot` → `CONTROLLED_PILOT_READY`, `production_candidate` → `PRODUCTION_CANDIDATE` (2026-09-24), `production` → **NOT_READY (9 red by design)**; last remote CI green **2026-09-29**, not re-asserted for current tree.

---

## 1. Blocker register

Severity: **P0** = claim-invalidating / data-safety / cannot-ship; **P1** = production-blocking but bounded; **P2** = hardening / hygiene; **P3** = cosmetic / documentation.

### A. Release-boundary and governance blockers (the "idea" itself)

| ID | Sev | Blocker | Evidence |
|---|---|---|---|
| BLK-001 | P0 | **Nine production-only gates are fail-closed red by design** (`signed_production_evidence`, `certified_data_isolation`, `external_observer_audit`, `production_deployment_architecture`, `disaster_recovery_evidence`, `operational_ownership`, `incident_oncall_ownership`, `security_review`, `legal_privacy_review`). A bare `PRODUCTION` label is unreachable; `docs/release/production-blockers.md` declares defeating a block a defect; `release/release-profiles.yaml` derives them as production-only. | `release/release-profiles.yaml`, `docs/release/production-blockers.md`, `docs/PRODUCTION_STATUS.md` |
| BLK-002 | P0 | **`production_approved` must be a genuine human sign-off**; the signoff module refuses simulation; the SOD matrix forbids one actor approving their own run. Any fabricated signature is explicitly a defect. | `docs/release/handoff/controlled-pilot-handoff-dossier.md` §7, `release/signoff.py` |
| BLK-003 | P0 | **No production deployment architecture**: no approved TLS/HA/secrets/network topology; Compose profile is single-host dev-shaped; the app binds loopback by design and is not internet-exposed; no infrastructure-as-code for production. | `release-boundary.md`, `infra/docker/*`, `docs/release/app-setup-guide.md` |
| BLK-004 | P0 | **No disaster-recovery evidence at production scale**: backup/restore verified locally (verify-only + restore isolated volume + checksum-tamper rejection), but no RPO/RPO-measured production drill, no offsite copy, no retention policy, no restore-time SLO. | `docs/release/app-tenant-ops-drill-2026-10-31.md`, `docs/release/backup-restore-guide.md` |
| BLK-005 | P0 | **No named operational owner / on-call / escalation contract**; solo operator; bus factor 1; `incident-response.md` exists but no rotation, no paging drill, no second responder. | `docs/release/production-blockers.md`, `docs/PRODUCTION_STATUS.md` |
| BLK-006 | P0 | **No independent security review / penetration test** of the production release; bandit/pip-audit/pre-commit are not a pen-test; no third party has attacked the running app. | `KNOWN_ISSUES.md` #10, `SECURITY.md` |
| BLK-007 | P0 | **No legal / privacy review** for real PII jurisdictions (GDPR/DSGVO): no DPA, no DPIA, no retention schedule, no DSR workflow exercised end-to-end on real data shapes. (Synthetic fixtures contain PII-*shaped* data, which is exactly why the review must exist before real data flows.) | `docs/release/production-blockers.md` |
| BLK-008 | P0 | **No certified data isolation**: driver-level (SQL) tenant partitioning is **not implemented**; isolation holds at the policy seam (`security/policy.py::authorize`) and at tested HTTP routes; no independent certification; no `tenant_id` filter enforced inside `Store`/`NodeStore` queries. | `docs/HELIX_CODEX_EXECUTION_STATUS.md` (C8), `KNOWN_ISSUES.md` #10 |
| BLK-009 | P0 | **No external observer audit** of the control plane / audit chain; hash-chain verified only by its own exporter; never observed by an independent party. | `docs/PRODUCTION_STATUS.md` |
| BLK-010 | P1 | **Dependency conflict breaks the dashboard on fresh install**: project pins `numpy>=1.24,<2` (hard bound, numeric-behavior reasons) but `streamlit` pulls `pyarrow`; `pyarrow>=26` refuses numpy 1.x at import → `st.dataframe` path crashes; **pyarrow is not declared anywhere in `requirements*.txt`/lock**, so every fresh install re-breaks. Fixed locally with `pyarrow==18.1.0`; must be pinned + locked + CI-gated. | measured 2026-11-03; `requirements.txt:40`, `pyproject.toml:32` |
| BLK-011 | P1 | **Fresh-install cockpit dead-ends**: `bootstrap_owner.py` created the domain with `client_id=NULL`; cockpit bridge refuses to compute ("no pack data can be scoped"); no documented path for a new operator to bind a client pack; fixed in-repo (`--client-id`, default domain; demo DB patched) but **no test pins it and the setup guide is stale**. | measured 2026-11-03; `helix_codex_app/integration/cockpit_bridge.py:85` |
| BLK-012 | P1 | **The App has no tenant-scoped CSV import/export workflow** (KNOWN_ISSUES #11). The 304 MB client fixtures are processed only by the readiness harness; an operator cannot load client data into the App; the drill used HTTP-created summaries instead. Until this exists, "the App runs on client data" is only true through a side harness. | `KNOWN_ISSUES.md` #11 |
| BLK-013 | P1 | **Agent dispatch surface returns fake output** (KNOWN_ISSUES #7): `app/command_center/agents/dispatch.py` — `# TODO` stubs return `f"Called {agent_name}…"`; args unvalidated; legacy regex parser behind `HELIX_LEGACY_CALL_PARSING=1`. The "nine AI agents route work" claim is false at this surface. | `KNOWN_ISSUES.md` #7 |
| BLK-014 | P1 | **Connector activation gate checks a constant**: `connectors/gateway.py:110` passes `provider_activated=True  # TODO`; the governance gate therefore cannot fail on an unactivated provider. | `KNOWN_ISSUES.md` #8 |
| BLK-015 | P1 | **Rate limiting trusts `x-helix-client-ip`**: correct only behind the Cloudflare Worker; if the app is ever exposed without it, the throttle is trivially spoofable; not unified with the login throttle. | `KNOWN_ISSUES.md` #6, `helix_codex_app/security/client_ip.py` |
| BLK-016 | P2 | **Cockpit UI tier quarantined** (19 tests deselected) and the live `ws /ws/v1/cockpit/stream` is tested but unused by the Streamlit UI (polls every 2 s instead); the "read-only cockpit readiness" claim is weaker than it looks. | `KNOWN_ISSUES.md` #9 |
| BLK-017 | P1 | **Engine correctness unproven by the suite**: 2,000 passing tests certify plumbing, not fitness of outputs for real organizations; no independent tenant-isolation audit; coverage floor ≠ correctness. | `KNOWN_ISSUES.md` #10 |
| BLK-018 | P1 | **62 uncommitted paths** (57 M + 5 ??): identity-scrub docs, readiness gate fixes, drill evidence, backup/restore changes — mixed concerns, unauditable release candidate; `repository_state` gate's "commit is attestable" property is weakened; no tag for the candidate. | `git status` 2026-11-03 |
| BLK-019 | P1 | **No remote CI on the current tree**; last recorded remote green 2026-09-29; README badge intentionally switched to "local verification"; a green badge cannot be cited for this code. | README.md badge block (diff), `docs/PRODUCTION_STATUS.md` |
| BLK-020 | P2 | **Lint debt in marketing tooling**: 20 ruff errors in `marketing/helix-codex-deck/video/*.py` (subprocess/urllib without S603/S310 guards, unused imports, loop-var capture); 2 unformatted files. Product code is clean, but a repo-wide CI lint gate is red. | measured 2026-11-03 |
| BLK-021 | P2 | **Ingest engine binds `0.0.0.0:8000` by default**; `HELIX_COCKPIT_ALLOW_UNAUTHENTICATED=true` exists and was set for local dev tonight; approve endpoint needs `HELIX_COCKPIT_APPROVE_KEY`; the override's blast radius is undocumented for operators; app itself is loopback-only (good). | `ingest_engine.py` module docstring, README |
| BLK-022 | P1 | **Real-client convergence unproven**: fixtures are synthetic; 1,500-seat shape, 2.7% ticket sample, Cairo-time business dates, Zendesk/Salesforce vendor-shaped raws — none of it has met a real client's drift, volume, schema evolution, or connector reality; every pass to date is `simulated_realistic`. | `External tenant data/*/00_START_HERE/DATA_CLASSIFICATION.md`, drill docs |
| BLK-023 | P2 | **Claims/docs posture is honest but contradictory after any "ready" flip**: README/index.html/PRODUCTION_STATUS/MASTER_STORY all say NOT_READY; a partial flip would create legal-grade misinformation; the flip must be total, disclosed, and machine-gated. | `index.html`, `README.md`, `docs/PRODUCTION_STATUS.md` |
| BLK-024 | P2 | **Solo-operator continuity**: no second person has ever run the runbook, restored a backup, or taken the pager; laptop loss = total operational knowledge loss; keys/secrets handling undocumented for break-glass. | `docs/release/operator-runbook.md`, dossier §8 |
| BLK-025 | P2 | **No observability/SLO/error-budget stack**: metrics exist locally; no alerting, no dashboards-as-code, no SLO, no incident drill measured against RTO/RPO; `observability/` is code, not an operated system. | `observability/`, `docs/release/incident-response.md` |
| BLK-026 | P2 | **Performance at real scale unproven**: latency budget gate (PR-G12) passed at fixture scale; no soak at 1,500-seat interval rates; CX reconciliation caveat (tickets 2.7% sample vs `queue_metrics_daily` authoritative) must survive contact with real volumes. | `consumer_contract.md`, `tests/test_engine_audit_perf.py` |
| BLK-027 | P2 | **Bootstrap password on argv** (`--password HelixDemo!2026`) → shell history / process-list exposure; no stdin/secret-file/env alternative; no rotation story. | `helix_codex_app/scripts/bootstrap_owner.py` |
| BLK-028 | P3 | **Readiness harness is path-fragile**: resolves fixtures via sibling dir or `HELIX_TENANT_DATA_DIR`; not in CI; not hermetic; evidence out dir defaults into repo; re-runs are manual. | `scripts/production_readiness/dataset.py` |
| BLK-029 | P2 | **No immutable, releasable artifact**: no registry push, no release manifest signing tied to a git tag; drill images (`helix-prime-codex-app:drill-*`) exist only locally; `release-manifest.json` is a candidate snapshot, not a shipped artifact. | `docs/release/app-tenant-ops-drill-2026-10-31.md`, `release/release-manifest.json` |
| BLK-030 | P3 | **Parent-project surfaces outside the two apps are untested tonight**: Helix Education (sibling L&D engine), Study Studio, L&D Command Center — referenced, not verified; sibling boundary (C7) is by design, but "Helix Codex OS is done" cannot be claimed from these two apps alone. | repo layout, `00_CONSTITUTION.md` |

### B. What is NOT a blocker (verified strengths to keep)

- Fail-closed gate design; append-only hash-chained audit ledger; provenance tagging (`simulated_realistic`); sample-data off by default; policy-seam authorization before storage; both drills passed; fixtures hash-verified; deterministic engine results; backup verification with tamper rejection; restore into isolated volume; rollback rehearsal; migration drift checks (63/63 app, 19/19 control plane); 128 focused tests + 2,000-test suite (recorded); product-code lint clean; dependency lock with hashes.

---

## 2. The one change the owner asked for — and its honest shape

**Owner directive (2026-11-03):** stop treating "a real external client + human approvals" as the gate for production readiness; prove readiness with simulated clients so that the real-client run later is the *same* run.

**What this report accepts:** the approval *evidence* for production may be produced by simulation; no human signature is required to declare the system ready **for the simulated-production profile**.

**What this report refuses to do:** fabricate a signature, mint a fake "external auditor" who is secretly this repo, claim GDPR compliance without a reviewer, or emit a bare `PRODUCTION` label. Those are not "changing the idea"; they are fraud against the future client.

**Resolution (carried into the plan):** a new release profile `simulated_production` whose gates are the *same engineering gates*, each bound to **machine-verifiable simulated evidence with mandatory disclosure**, producing the classification **`SIMULATED_PRODUCTION_READY`** — never `PRODUCTION`. The real client's arrival triggers an **activation runbook** that re-executes the identical harness against real data; at that point (and only that point) a human/legal/external sign-off is recorded, flipping `SIMULATED_PRODUCTION_READY → PRODUCTION`. Details: `AUTONOMOUS_REMEDIATION_PLAN_2026-11-03.md` §4.

---

## 3. Blocker → plan coverage map

Every blocker above is mapped to a phase in the companion plan; nothing is fixed by assertion.

| Blockers | Plan phase |
|---|---|
| BLK-018, BLK-019, BLK-020 | Phase 0–1 (freeze, baseline, CI-equivalent gate, repo-wide lint) |
| BLK-010, BLK-011, BLK-027 | Phase 2 (dependency pin + bootstrap docs/tests + secret-safe bootstrap) |
| BLK-013, BLK-014, BLK-015, BLK-021 | Phase 2 (real dispatch or honest removal; connector activation from state; header trust fix; loopback default + docs) |
| BLK-008 | Phase 3 (driver-level tenant isolation + cross-tenant attack suite) |
| BLK-012 | Phase 4 (App CSV import path) |
| BLK-001, BLK-002, BLK-009 | Phase 5 (simulated approval architecture; new profile; signed simulation evidence; verification script) |
| BLK-003, BLK-004, BLK-029 | Phase 6 (simulated production topology; DR drill; immutable artifact) |
| BLK-005, BLK-006 | Phase 7 (simulated ops/on-call drill; simulated security review; simulated legal/privacy review — all disclosed) |
| BLK-016, BLK-017 | Phase 7–8 (un-quarantine UI tier or justify; engine-correctness harness: golden vectors, property tests, cross-check vs independent implementation) |
| BLK-022, BLK-026, BLK-028 | Phase 8 (scale/soak; CI-wired readiness harness; drift monitors) |
| BLK-023, BLK-024, BLK-025 | Phase 9 (docs/claims flip with disclosure; runbook drill by "second operator" = clean-room rehearsal; SLOs + alerts-as-code) |
| BLK-007, BLK-030 | Phase 9 (activation runbook; sibling-service boundary re-check; final gauntlet) — residual, disclosed |

**Residual risk that cannot be closed without reality itself:** a bare `PRODUCTION` label and any claim about a real client's data. The plan converts these from *silent assumptions* into *explicit, dated, verifiable activation steps*.
