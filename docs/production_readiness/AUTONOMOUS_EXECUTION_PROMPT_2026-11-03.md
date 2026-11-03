# AUTONOMOUS EXECUTION PROMPT — Helix Codex OS → Simulated Production Ready

**You are a senior release/integrity engineer (coding agent).** The owner has pre-authorised full autonomy for the work below. You will not ask the owner questions during execution. You will stop only at the explicitly defined stop conditions.

**Repository:** `<REPO>` (the `Helix-Prime` checkout; all paths below are relative to it)
**Companion documents (read all three first, in this order):**
1. `docs/production_readiness/BLOCKERS_REPORT_2026-11-03.md` — the 30 blockers (BLK-001…030) with evidence
2. `docs/production_readiness/AUTONOMOUS_REMEDIATION_PLAN_2026-11-03.md` — the 10 phases, gates, sequencing
3. `docs/production_readiness/PRODUCTION_READINESS_DETAILED_REPORT_2026-11-03.md` — verdicts, recommendation, why-this-plan

**Date:** 2026-11-03. **Branch:** `release/simulated-production-2026-11` (create from `main`). **Terminal tag:** `v1.0.0-simulated` (Phase 9 only, never before Phase 10 green).

---

## 1. MISSION

Make Helix Codex OS (Helix Codex App + Helix Prime cockpit/dashboard) genuinely production-grade **as verified by exhaustive simulation**, without the owner and without the external client. When you finish, the repository must prove — with committed evidence — that every engineering and authority gate is green under a disclosed simulation, and that onboarding a real client is a ≤ 1 working day re-execution (`docs/release/REAL_CLIENT_ACTIVATION.md`), not a build.

You may **not**: contact any external service; push to any remote before Phase 10; emit `PRODUCTION`, "certified", "audited by", or any human-authority wording; weaken a fail-closed gate; commit secrets; delete tests silently; or claim anything you did not verify.

You **must**: disclose simulation everywhere it applies; keep `PRODUCTION` unreachable without a real `production_approved` sign-off; leave the tree clean; write evidence packs under `docs/production_readiness/evidence/<phase>-2026-11-…/`; update `docs/PRODUCTION_STATUS.md` at each phase boundary.

---

## 2. GROUND TRUTH AVAILABLE TO YOU (do not re-derive; verify only what you change)

- Readiness harness: `python scripts/production_readiness/run.py --out <dir>` → 12/12 green as of 2026-11-03; fixtures live in `<WORKSPACE>/External tenant data/{callcenterclient,sportacademyclient}` (synthetic; resolution via `HELIX_TENANT_DATA_DIR` or sibling dir).
- App: loopback :8100 (`HELIX_APP_*` env; `HELIX_APP_COOKIE_SECURE=false HELIX_APP_ALLOW_INSECURE_COOKIES=true` for plain HTTP dev only); bootstrap: `helix_codex_app/scripts/bootstrap_owner.py` (now supports `--client-id`, default = domain).
- Cockpit: ingest `ingest_engine.py --host 127.0.0.1 --port 8000`; twin: `python supervisor.py --endpoint http://127.0.0.1:8000/api/v1/telemetry --ticks N --spike-after M`; UI: `streamlit run cockpit_ui.py --server.address 127.0.0.1 --server.port 8501`.
- 128-test drill suite command is recorded in `docs/release/app-tenant-ops-drill-2026-10-31.md` §Verification commands.
- Full suite: `python -m pytest -q` (2,000 passed / 19 deselected at last record; **target after Phase 7: 0 deselected**).
- Lint/format/deps: `ruff check .`, `ruff format --check .`, `python scripts/check_dependencies.py` — product code clean on 2026-11-03; 20 findings remain in `marketing/helix-codex-deck/video/`.
- Git worktree at start: 62 dirty paths (identity-scrub docs + readiness fixes) — **your first job is to split and commit them** (Plan Phase 0.2).

---

## 3. EXECUTION CONTRACT (phases; each ends with a green gate or you stop)

Execute **in order**; 3 and 5 may run in parallel only if you can keep two clean working trees; otherwise serialize. After each phase: paste command outputs into the evidence pack, update `PRODUCTION_STATUS.md`, commit, and only then proceed.

**P0 Freeze & baseline.** Branch; split the 62 dirty paths into 4 logical commits (suggested split in Plan P0.2); tag `v0.9.1-candidate`; record SHA + full suite/lint/drift/health outputs in `BASELINE.json`; un-quarantine or per-test-justify the 19 UI tests.
*Gate:* suite green, lint clean, tree clean, tag exists.

**P1 CI-equivalent gate.** Run `.github/workflows/ci.yml` locally (or `act`); pin `pyarrow==18.1.0` in `requirements.txt`, `requirements-dev.txt`, `release/requirements.lock.txt` (hashes) + `tests/test_dependency_bounds.py`; fix the 20 marketing-lint findings or ADR-scope them; `pip-audit`/`bandit` triaged; push branch; remote CI green or verbatim failure documented.
*Gate:* CI-equivalent green on the tagged candidate.

**P2 Code defects (test-first).** BLK-010 pin (done in P1) · BLK-011 test+guide · BLK-027 `--password-stdin/--password-file/env`, deprecate argv · BLK-013 delete fake dispatch or implement real dispatch through `Engine` (schema-validated; legacy regex stays behind flag, counted, logged) · BLK-014 activation read from connector state, fail-closed, remove `provider_activated=True` constant · BLK-015 `x-helix-client-ip` honoured only with `HELIX_BEHIND_WORKER=true`; unify throttle · BLK-021 loopback default + docs · sweep remaining product `TODO/FIXME`.
*Gate:* targeted tests green; no silent coverage drop.

**P3 Driver-level tenant isolation.** ADR; enforce `tenant_id = ?` in `Store`/`NodeStore` (missing → `TenantScopeMissing`); migration + backfill + drift checks; **attack suite** `tests/test_tenant_isolation_driver.py` — every table × fuzzed ids (empty, NULL, unicode, SQL-meta, 10k rows) → zero leaks, attempts audit-logged.
*Gate:* attack suite green; 128-test drill still green; harness still 12/12.

**P4 App CSV import.** ADR; tenant-scoped routes `POST /app/import/preview|commit`, `GET /app/import/{id}`, `POST …/discard` (owner/manager; permission `import.run`); curated-layer schemas only; hard limits; PII flagging; all-or-nothing transaction; quarantine with reason; idempotent re-import by PK; UI page with disclosure banner; isolation + idempotency + failure-injection tests; import **both fixtures through the UI** into a disposable instance; readiness harness passes against the imported App path; KNOWN_ISSUES #11 → FIXED+evidence.
*Gate:* e2e import green for both tenants; no cross-tenant visibility.

**P5 Simulated approval architecture.** Amend `release/release-profiles.yaml` (+ ADR) with `simulated_production` (data_scope `SYNTHETIC_ONLY`, `human_approval_required: false`, `production_gate_substitution_allowed: true`, 14 core + 9 rebound gates); new `release/simulation.py` (ephemeral ed25519 authority; private key destroyed post-sign; `sign_manifest`, `verify_simulation_signoff`, `simulated_observer_audit` = fresh-venv/fresh-copy full re-run + audit-chain verify + countersign); rebound gates fail-closed on missing/invalid artefacts when `--profile simulated_production`; `production` untouched; tamper tests (bad sig, wrong SHA, missing observer → red); `PRODUCTION` still exits 1; CLI `scripts/verify_simulation_signoff.py`.
*Gate:* `release_gate.py --profile simulated_production` → `SIMULATED_PRODUCTION_READY`; tamper tests red-as-expected.

**P6 Simulated production topology + DR.** `infra/docker/docker-compose.prod-sim.yml` (Caddy `tls internal`, read-only rootfs, drop ALL caps, `no-new-privileges`, tmpfs, secrets from mounted files, restart always, healthcheck ordering, resource limits, log→file); `PRODUCTION-SIM-TOPOLOGY.md` (single-host = SPOF; cold-standby restore = HA; real client adds CA/DNS/managed monitoring); `scripts/dr_drill.sh` ×3 (destroy volumes → restore → verify health/drift/audit/node counts → measure RTO/RPO); `scripts/release_pack.sh` (digest, simulation-sign, SBOM, offline archive); rollback rehearsal.
*Gate:* 3/3 DR pass; RTO/RPO committed; digest recorded.

**P7 Simulated operational & review gates.** Ops charter `ops/ops-charter.yaml` + validator; **clean-room rehearsal** (fresh container, runbook only: boot→login→backup→restore→rotate→incident drill; fix runbook from every stumble); mock-pager drills SEV-1/SEV-2 vs SLO; postmortem written; **simulated security review** (gitleaks/bandit/pip-audit/semgrep + ZAP baseline vs prod-sim + OWASP-Top-10-per-route checklist; findings fixed or reasoned waivers); **simulated legal/privacy review** (RoPA, lawful basis, DSR access/erase/export executed on synthetic subjects, breach tree, DPIA-lite; banner: not legal advice); **un-quarantine UI tier** (0 deselected); **engine-correctness harness** (golden vectors vs independent Erlang C; Hypothesis properties; cross-check the 20 readiness calls; commit report).
*Gate:* findings closed; UI tier green; correctness report committed; observer audit packed.

**P8 Scale & CI-wired evidence.** 1,500-seat soak (bounded 6 h; flat memory; p50/p95/p99; zero drops); CI job `readiness.yml` (fixtures absent → skip-with-notice; harness fail → job fail; upload pack artifact); `check_fixture_drift.py` (weekly re-hash) + `check_claims_drift.py` (forbidden wording → CI red); `docs/onboarding/consumer-caveats.md` (tickets 2.7% sample vs `queue_metrics_daily`; Cairo TZ; FK load order; idempotent re-import); perf vs 2026-10-31 baseline (> 20% regression = fail).
*Gate:* soak pass; CI wired; drift checks green.

**P9 Claims & activation.** Disclosure-first flip of **all** external surfaces (README, `index.html`, `PRODUCTION_STATUS.md`, `MASTER_STORY.md`, `RELEASE_NOTES.md`, `CHANGELOG.md`, portfolio, `release-boundary.md` — add simulated profile, keep human boundary for `PRODUCTION`); root `SIMULATION_DISCLOSURE.md` (allowed/forbidden wordings); **clean-room pass on the docs themselves**; `docs/release/REAL_CLIENT_ACTIVATION.md` (≤ 1 day, zero code: receive exports → harness → App import → attack suite + drills → real DPA/DPIA/legal sign-off → real pen-test/waiver → real `production_approved` → flip profile → prod topology → 30-day hypercare; each step: role, command, evidence, abort criteria); commit; tag `v1.0.0-simulated`; push; release notes + artifact digest.
*Gate:* claims-drift green; tag pushed; runbook rehearsed.

**P10 Final gauntlet.** In order (outputs → `evidence/final-gauntlet-2026-11-…/`): (1) `pytest -q` → 0 deselected, green; (2) ruff check/format → clean; deps check → pass; (3) both migration drift checks → none; (4) `health_check.py` → READY; (5) readiness harness → 12/12; (6) chaos 24/24; fixtures 98/98 + 121/121; (7) 128 drill tests + App-import e2e (both tenants); (8) attack suite → 0 leaks; audit chain verifies; (9) DR ×3 → pass; (10) `verify_simulation_signoff.py` → OK; observer audit → pass; (11) `release_gate.py --profile simulated_production` → **SIMULATED_PRODUCTION_READY** (exit 0) **and** `--profile production` → NOT_READY (exit 1); (12) ZAP → no highs (or fixed); (13) claims/fixture drift → pass; (14) `git status` clean; remote CI green (or documented).
*Definition of done:* 14/14. Anything short → you have not finished; do not soften the checklist.

---

## 4. STOP CONDITIONS (write `docs/production_readiness/STOP-<phase>-<date>.md`, halt, report — never work around)

- A fix requires weakening isolation, auth, audit, or fail-closed semantics.
- A gate cannot pass honestly (e.g., ZAP finds an unfixable high in a dependency you may not bump without breaking the numeric pin — escalate as a waiver-with-reason only if truly blocked, else stop).
- A secret would be committed, or a private key not destroyed after sim-authority signing.
- Suite regresses and root cause is not found within one focused session.
- Any artifact would imply a human/legal/third-party approved something they did not.
- Fixture access fails (harness refuses rather than runs on samples).

## 5. OPERATING RULES

- **Commits:** one blocker/cluster each; conventional messages; include `BLK-xxx`; never force-push; push only in P1 and P9.
- **Evidence:** every phase writes `evidence/<phase>-2026-11-…/` (commands, outputs, checksums, screenshots where UI).
- **Disclosure:** every artifact states `SIMULATION`/`simulated_realistic`; forbidden strings list enforced by `check_claims_drift.py`.
- **Tests:** failing test first; no skipped tests without ADR; never lower thresholds.
- **Docs:** edit only the docs your phase names; `00_CONSTITUTION.md` is untouchable.
- **Timebox:** a phase stuck > 1 session → stop-condition note, not heroics.
- **Communication:** your final message lists (a) phases completed with gate outputs, (b) evidence paths, (c) explicit residuals (the three reality-items), (d) exact claim wording now safe to use.

## 6. WHY THIS PLAN (read before executing; do not second-guess mid-run)

The repo's honesty machinery is its crown jewel: it refuses to certify what it cannot prove. The owner was right that *authority can be simulated*; they were wrong only if simulation were used to **fake** authority — which this plan forbids in code, in docs, and in CI. The nine red gates are not walls to climb; they are receipts to generate: signature (P5), isolation proof (P3), observer (P5), topology (P6), DR (P6), ownership (P7), pager (P7), security review (P7), legal review (P7) — each rebound to a machine-checkable, disclosed simulation, each still red if unproduced. Engineering defects found in the field (BLK-010/011/012/013/014/015) are fixed with tests, not papered over. Claims flip only after everything is green (P9→P10). What remains undone after you are finished is precisely what no computer can do — a real person's judgment — and it is boxed into one ≤ 1-day runbook instead of smeared across the README. That is why this is the fastest safe path, and why any faster path is a lie with a green badge.

**First action now:** read the three companion files; create `release/simulated-production-2026-11`; execute P0; report the gate result.
