# Helix Codex OS — Autonomous Remediation Plan (2026-11-03)

**Mission:** take Helix Codex OS (Helix Codex App + Helix Prime dashboard/cockpit, six engines, nine agents, control plane, release gate) from `CONTROLLED_PILOT_READY` / `NOT_READY` to a fully-remediated, exhaustively-tested, packaged state whose only remaining delta to production is **reality itself** — executed **without the owner and without the external client**, by a coding agent, with every step machine-verifiable and every claim disclosed.

**Owner pre-authorisation:** the owner has explicitly directed (2026-11-03) that the "real client + external approvals" precondition be replaced by simulated proof; the owner will not participate in execution and does not need to; nothing may wait on the owner. Where the plan would otherwise need a human (sign-off, legal review, on-call), it is satisfied by a **disclosed simulation** or replaced by an **activation step for the real client** — never by a fabricated human.

**Companion files:** blockers → `BLOCKERS_REPORT_2026-11-03.md`; combined decision document → `PRODUCTION_READINESS_DETAILED_REPORT_2026-11-03.md`; agent execution prompt → `AUTONOMOUS_EXECUTION_PROMPT_2026-11-03.md`.

---

## 0. Ground rules (non-negotiable)

1. **No fabrication.** No invented humans, signatures, audits, certifications, or dates. Simulation artefacts carry `SIMULATION` / `simulated_realistic` labels and `simulation: true` machine markers; docs carry a banner.
2. **No bare `PRODUCTION`.** The new terminal classification for this work is `SIMULATED_PRODUCTION_READY`. Only a real client + real human/legal/external sign-off flips it to `PRODUCTION` (activation runbook, Phase 9.4).
3. **Fail-closed everywhere.** Any red gate → stop → fix → re-run. Never weaken a gate to make it pass. Changing a gate's *definition* requires an ADR in `docs/adr/` and a pinning test.
4. **Disclosure travels with the artefact.** Every evidence pack, image, manifest and doc produced here keeps the synthetic-data disclosure.
5. **TDD or it didn't happen.** Every fix lands with a failing-then-passing test (or an explicit "already pinned by <test>" note).
6. **Small, reviewable commits.** One blocker (or tightly-coupled cluster) per commit; conventional messages; no force-push; push only after the full gauntlet (Phase 10) unless the owner asks.
7. **Stop conditions** (stop, write a blocker note in `docs/production_readiness/`, do **not** work around): (a) a fix would require weakening isolation/auth/audit; (b) a gate cannot pass honestly; (c) a secret would have to be committed; (d) the suite regresses and the cause is unclear; (e) any step would mislabel simulation as human authority.
8. **Timeboxing.** Each phase ends with a dated evidence pack under `docs/production_readiness/evidence/<phase>-2026-11-…/` and an updated `PRODUCTION_STATUS.md` entry.

---

## 1. Target architecture of the change (the "idea", done honestly)

Today: `release/release-profiles.yaml` → `production` requires 23 gates; 9 of them need outside-the-building authority → unreachable → `NOT_READY` forever.

After this plan:

```
release/release-profiles.yaml
  └─ profile: simulated_production            (new)
       canonical_surface: helix-app+helix-api
       data_scope: SYNTHETIC_ONLY             (unchanged semantics)
       human_approval_required: false         (simulation authority instead)
       production_gate_substitution_allowed: true   (each substitution is defined, tested, disclosed)
       evidence_expiry_days: 30
       required_gates: [all 14 core] + [all 9 production-only, rebound]
```

The nine formerly-external gates are **rebound, not deleted**:

| Former gate | Simulated evidence (machine-verifiable) | Disclosure |
|---|---|---|
| `signed_production_evidence` | Ephemeral **simulation authority** keypair per candidate (generated in a clean temp dir, private key destroyed after signing, public key + fingerprint committed); sign the release manifest + evidence pack; `scripts/verify_simulation_signoff.py` re-verifies offline | "Signed by simulation authority <fp>; not a human or third party" |
| `certified_data_isolation` | **Driver-level tenant filters** implemented in `Store`/`NodeStore` (mandatory `tenant_id = ?` on every query; fail-closed when unset) + **cross-tenant attack suite**: for every table, attempt read/write/update/delete with a foreign tenant id → 0 leaks; fuzzed ids; evidence JSON | "Isolation verified by machine on synthetic data; not an independent certification" |
| `external_observer_audit` | **Two-key rehearsal**: a second, independent process (separate venv, separate DB copy, separate working dir — optionally separate machine/VM) re-runs every gate and verifies the audit hash-chain; its report is countersigned by the simulation authority | "Observer was simulated; no third party participated" |
| `production_deployment_architecture` | **Simulated production topology**: `infra/docker/docker-compose.prod-sim.yml` — Caddy (TLS, loopback or test-CA certs), app behind it, read-only root FS, dropped caps, no new privileges, restart policies, healthchecks, secrets via mounted files, log shipping to local sink; HA documented as single-host + cold-standby restore (measured), or k3s manifest if available | "Topology simulated locally; not operated by a provider" |
| `disaster_recovery_evidence` | **DR drill**: full backup → destroy volumes → restore into clean env → verify hashes/migration drift/audit chain → measure RTO/RPO → repeat ×3 → pack | "DR measured on synthetic data locally; production RPO/RTO unproven until real run" |
| `operational_ownership` | **Ops charter simulation**: owner roster encoded as data (`ops/ops-charter.yaml`: roles, rotations, escalation ladder, SLAs), validated by `scripts/validate_ops_charter.py`; **clean-room rehearsal**: a scripted "second operator" follows only the runbook to boot, backup, restore, rotate, and incident-drill; gaps found are fixed in the runbook | "Roster simulated; no human is on call" |
| `incident_oncall_ownership` | **Paging drill**: local mock pager (file/webhook sink); inject a SEV-1 (audit-chain verify failure) and SEV-2; measure ack/resolve against SLO; write the postmortem; fix runbook | "Pager simulated; no human was paged" |
| `security_review` | **Simulated review**: `bandit`, `pip-audit`, `semgrep` (if installable), `gitleaks`, plus **OWASP ZAP baseline** against the running app + manual checklist of the OWASP Top-10 mapped to routes (auth, CSRF, tenant isolation, headers, sessions, cookies, SSRF, upload); every finding fixed or waived-with-reason; pack | "Not a human pen-test; findings fixed as found" |
| `legal_privacy_review` | **Checklist-driven review** (GDPR/DSGVO articles mapped to data flows: lawful basis, minimisation, retention, DSR access/erase/port, DPIA-lite for synthetic PII, breach notification); output = signed memo; gaps → tickets; **explicitly NOT legal advice** | "Not legal advice; real review required before real PII" |

`release/gate.py` learns one new terminal label:

```
all 14 core green + all 9 rebound green + verify_simulation_signoff.py ok
    → SIMULATED_PRODUCTION_READY   (exit 0; docs/production_readiness/evidence/…)
any red                          → NOT_READY (exit 1)   [unchanged fail-closed]
```

`PRODUCTION` remains unreachable without a real `production_approved` sign-off (unchanged code path, unchanged refusal). The owner gets the honest, strong claim instead: *"every engineering gate is green, every authority gate is simulated-and-disclosed, and the real-client run is a re-execution, not a build."*

---

## 2. Phased execution plan

### Phase 0 — Freeze, baseline, attestable candidate (½ day)

**0.1** `git checkout -b release/simulated-production-2026-11` from `main`; `git stash list` empty.
**0.2** Commit the 62 dirty paths **in logical order**, not one blob:
 1. `fix(release): backup/restore/gate changes for node-store coverage` (`release/gate.py`, `release/backup.py`, `tests/test_c8_release_gate.py`, `tests/test_api_tenant_scope.py`, `helix_codex_app/scripts/{backup,restore}_app.py`, `tests/helix_codex_app/test_backup_procedure.py`, `infra/docker/*`, `tests/test_docker_compose_security.py`)
 2. `docs: readiness evidence and drill record (2026-10-31)` (`docs/production_readiness/*`, `docs/PRODUCTION_STATUS.md`, `docs/HELIX_CODEX_EXECUTION_STATUS.md`, `docs/KNOWN_ISSUES.md`, identity-scrub docs, portfolio)
 3. `docs: add 2026-11-03 blockers report, plan, detailed report, execution prompt`
 4. `fix(app): bootstrap --client-id so a fresh install is cockpit-ready` (`helix_codex_app/scripts/bootstrap_owner.py`)
**0.3** Tag `v0.9.1-candidate` on the result; `git status` clean; record SHA in `docs/production_readiness/evidence/phase0-*/BASELINE.json`.
**0.4** Re-run full suite (`-p no:cacheprovider`), `ruff check .`, `ruff format --check .`, `scripts/check_dependencies.py`, both migration drift checks, `scripts/health_check.py` → paste outputs into `BASELINE.json`.
**0.5** Un-quarantine the 19 UI tests OR document a dated justification per test (skip ≠ silent pass). Target: suite green with **0 deselected**.

**Gate to proceed:** suite green, lint clean, tree clean, tag exists.

### Phase 1 — CI-equivalent gate on the candidate (½ day)

**1.1** Run the exact CI workflow locally (`.github/workflows/ci.yml` steps 1–17) or `act`; fix any drift; record.
**1.2** Pin `pyarrow==18.1.0` in `requirements.txt` **and** `release/requirements.lock.txt` (with hashes) **and** `requirements-dev.txt`; add a comment tying it to the numpy<2 bound; add `tests/test_dependency_bounds.py` asserting `import pyarrow` works with the installed numpy (fail loudly otherwise).
**1.3** Repo-wide lint to zero: fix the 20 `marketing/helix-codex-deck/video/*.py` findings (guard subprocess calls, drop unused imports, fix loop capture) or move that tree under a justified per-directory ignore with an ADR; `ruff format` the 2 files; enforce `--output-format github` in CI.
**1.4** `pip-audit` + `bandit -r` on the candidate; triage; pin fixes; record.
**1.5** Push branch; confirm remote CI green (or document the runner failure verbatim and fix it — do not claim green).

**Gate to proceed:** CI-equivalent all green on the tagged candidate; `BUILD.json` recorded.

### Phase 2 — Fix the code defects (1–2 days)

For each: failing test first → fix → pin → commit.

**2.1 (BLK-010)** Covered by 1.2; add `docs/DEVELOPMENT.md` note: "do not bump numpy past the hard bound without re-baselining every numeric engine test".
**2.2 (BLK-011)** Add `tests/helix_codex_app/test_bootstrap_client_id.py`: fresh bootstrap with `--client-id`/default → cockpit bridge computes; without → typed error. Update `docs/release/app-setup-guide.md` Step 5 with `--client-id` (default = domain) and a "cockpit shows no pack data" troubleshooting entry.
**2.3 (BLK-027)** `bootstrap_owner.py`: accept `--password-stdin` / `--password-file` / `HELIX_OWNER_PASSWORD` env; deprecate argv `--password` (warn); never echo; update guide.
**2.4 (BLK-013)** `app/command_center/agents/dispatch.py`: delete the fake-return stubs; implement real dispatch through `Engine`/scaffolds **or**, if the surface is unused, remove it and its route, leaving an ADR. Unvalidated dispatch → schema-validate args against the tool schema; legacy regex parser stays behind the env flag but is logged and counted; add tests for both paths.
**2.5 (BLK-014)** `connectors/gateway.py`: read provider activation from `ConnectorState`/registry (the same source the cockpit/ops surface shows); fail closed when unknown; add tests: unactivated provider → gate denies; activated → passes; unknown → deny. Remove the `# TODO` constant.
**2.6 (BLK-015)** `client_ip.py`: trust `x-helix-client-ip` **only** when `HELIX_BEHIND_WORKER=true` (explicit opt-in, documented); otherwise use `request.client.host`; unify with the login throttle or delete the duplication note; tests for spoofed header with and without the flag.
**2.7 (BLK-021)** `ingest_engine.py`: default bind `127.0.0.1` (keep `--host 0.0.0.0` explicit for containers); README + runbook updated; add `tests/test_ingest_default_bind.py`. Review `HELIX_COCKPIT_ALLOW_UNAUTHENTICATED`: emit a startup warning with a pointer to `HELIX_COCKPIT_APPROVE_KEY`; never needed in prod; document.
**2.8** Close any remaining `TODO`/`FIXME` in product paths (`grep -rn 'TODO\|FIXME\|HACK\|XXX' --exclude-dir=.venv --exclude-dir=marketing`); each → fixed, tracked, or ADR-waived.

**Gate to proceed:** all targeted tests green; no new skips; coverage on touched modules ≥ prior baseline.

### Phase 3 — Driver-level tenant isolation (1 day)

**3.1** ADR: `docs/adr/ADR-00X-driver-level-tenant-isolation.md` — decision, threat model, migration plan, rollback.
**3.2** Implement mandatory tenant scoping in `control_plane/store.py::Store` and `server/models/store.py::NodeStore`: every `SELECT/UPDATE/DELETE` carries `tenant_id = ?`; a missing/None tenant raises `TenantScopeMissing`; INSERT stamps `tenant_id` from the caller, never from payload; audit event on every scoped write.
**3.3** Migration: add `NOT NULL` constraints/indexes where missing (`tenant_id`); backfill from existing rows; `check_migration_drift.py` green; rollback = down-migration restoring nullability.
**3.4** **Cross-tenant attack suite** `tests/test_tenant_isolation_driver.py`: for **every** table in both DBs, iterate foreign tenant ids (incl. `""`, `NULL`, 10k rows, unicode, `../`, SQL-meta) → assert zero rows returned/affected; assert attempts are audit-logged; assert the error path fails closed.
**3.5** Re-run App/API drills (128-test set) + readiness harness; update `docs/HELIX_CODEX_EXECUTION_STATUS.md` C8 row honestly ("driver-level partitioning implemented and attack-tested on synthetic data; not independently certified").
**3.6** Evidence pack `phase3-*/isolation-attack-results.json` (counts, ids attempted, zeros).

**Gate to proceed:** attack suite green; no regression; pack committed.

### Phase 4 — App CSV import path (1 day)

**4.1** ADR: scope, formats (curated layer only: `16_DATA/curated/*.csv`), size limits, MIME/encoding checks, quarantine semantics.
**4.2** Routes (tenant-scoped, owner/manager only): `POST /app/import/preview` (parse + schema check + row-level errors), `POST /app/import/commit` (write to tenant import table + provenance `simulated_realistic` + audit), `GET /app/import/{id}` (status), `POST /app/import/{id}/discard`.
**4.3** Validation: header match against `16_DATA/schemas/*.json`; per-column type/range checks; FK resolution report (agents↔rosters, queue_metrics↔dates); PII columns hashed/flagged; reject on any hard error; soft warnings returned.
**4.4** Quarantine: failed files land in tenant-isolated quarantine with reason; never partially applied (all-or-nothing transaction); re-upload replaces by primary key (idempotent re-import).
**4.5** UI: `/app/import` page (progress, errors table, disclosure banner "synthetic data only in this environment"); nav entry behind permission `import.run`.
**4.6** Tests: unit (schema, parsers), integration (HTTP upload of both tenants' real curated files from `External tenant data`), isolation (cross-tenant import invisible), idempotency (re-upload), failure injection (truncated file, wrong encoding, 10k bad rows).
**4.7** Docs: `docs/release/app-data-import.md`; operator runbook updated; KNOWN_ISSUES #11 → FIXED with evidence.
**4.8** Prove end-to-end: import `callcenterclient` + `sportacademyclient` curated sets into a **disposable** instance; run readiness harness **against the imported App DB** (extend `scripts/production_readiness/run.py --via-app` or a twin path) → 12/12 green; screenshots attached.

**Gate to proceed:** import proven on both tenants through the App UI; evidence pack; no leakage between tenants.

### Phase 5 — Simulated approval architecture (1–2 days)

**5.1** ADR: `ADR-00Y-simulated-production-profile.md`; amend `release/release-profiles.yaml` (`simulated_production`, `profile_policy` as in §1); `release/profiles.py` derives; `tests/test_c8_release_gate.py` extended (profile exists; PRODUCTION still unreachable; `SIMULATED_PRODUCTION_READY` only when all rebound gates green).
**5.2** New module `release/simulation.py`:
 - `generate_simulation_authority(dest)` — ephemeral ed25519 keypair in temp dir; private key **destroyed** after use; fingerprint printed.
 - `sign_manifest(manifest_path, authority_dir)` — signs `release/release-manifest.json` + evidence pack checksums (`checksums.sha256`); writes `simulation_signature.json` (fingerprint, pubkey, timestamp, candidate SHA, simulation:true, disclosure).
 - `verify_simulation_signoff(pack_dir)` — offline re-verification; nonzero on any mismatch.
 - `simulated_observer_audit(repo_root, out)` — re-runs gates in a **fresh venv** in a **fresh temp copy** of the candidate; compares every gate verdict; verifies audit hash-chain; writes observer report; countersign.
**5.3** Rebound gates in `release/gate.py`: when profile == `simulated_production`, each production-only gate calls its simulation verifier; any missing/invalid artefact → gate red (fail-closed). When profile == `production`, behaviour **unchanged** (real sign-off only).
**5.4** `scripts/verify_simulation_signoff.py` CLI; `Makefile`/`scripts/release_simulation.sh` orchestration; both documented.
**5.5** Tests: tampered signature rejected; missing observer report → red; wrong candidate SHA → red; private key not left on disk (assert); `PRODUCTION` still exits 1; `SIMULATED_PRODUCTION_READY` exits 0 only with full pack.
**5.6** Disclosure kit: `SIMULATION_DISCLOSURE.md` (root), banner injection into evidence exporter, README/index.html/`docs/release/*` updated to reference it.

**Gate to proceed:** gate emits `SIMULATED_PRODUCTION_READY` on the full pack; all tamper tests red-as-expected; no path emits `PRODUCTION`.

### Phase 6 — Simulated production topology + DR (1 day)

**6.1** `infra/docker/docker-compose.prod-sim.yml`: Caddy TLS (internal CA, `tls internal`), app + api + caddy, read-only rootfs, `cap_drop: ALL`, `no-new-privileges`, tmpfs for writable paths, healthcheck-conditional ordering, restart `always`, resource limits, log driver → local file, secrets from `/run/secrets/*` (file-mounted, `0600`).
**6.2** `infra/docker/PRODUCTION-SIM-TOPOLOGY.md`: single-host topology diagram, TLS termination, backup cron, log rotation, patching cadence, break-glass; explicit statement: "single host = single point of failure; cold-standby restore is the HA story; measured RTO/RPO below; a real client deployment adds managed DNS/CA/monitoring".
**6.3** **DR drill ×3**: `scripts/dr_drill.sh` — stop stack → destroy volumes → restore latest verified backup → bring up → verify (`/app/healthz`, migration drift, audit chain, tenant node counts) → measure wall-clock RTO; compute RPO from newest restorable backup age; write `dr-report.json` (runs, timings, pass/fail). Failures → fix restore tooling → re-drill.
**6.4** **Immutable artifact**: `scripts/release_pack.sh` — build image, tag `helix-prime-codex:v0.9.1-sim`, export digest, `cosign`-style local sign or simulation-authority sign, generate `release/release-manifest.json` (commit, digests, gates, disclosure), attach SBOM (`syft` if available, else `pip freeze` + image digest), archive offline under `release/artifacts/` (gitignored) + `docs/production_readiness/evidence/phase6-*/`.
**6.5** Rollback rehearsal on prod-sim: v0.9.0-sim → v0.9.1-sim → rollback; verify data retention; record.

**Gate to proceed:** 3/3 DR drills pass; RTO/RPO recorded; artifact digest committed; rollback clean.

### Phase 7 — Simulated operational & review gates (1–2 days)

**7.1 (BLK-005/024) Ops charter + clean-room rehearsal.** Author `ops/ops-charter.yaml` (owner, backup owner="simulated operator", rotation weekly, escalation L1→L2→vendor, SLAs: SEV-1 ack 15 min/resolve 4 h, SEV-2 1 h/24 h). `scripts/validate_ops_charter.py` checks completeness/consistency. **Clean-room rehearsal**: fresh machine/container, only runbook access, boot → login → backup → restore → rotate credentials → incident drill; every stumble → runbook fix; log to `clean-room-rehearsal.md`.
**7.2 (BLK-005) Paging drill**: local mock pager; inject SEV-1 (audit chain verify fail) and SEV-2 (app 5xx); measure detection→ack→mitigate→resolve; SLO check; postmortem template filled; runbook updated.
**7.3 (BLK-006) Simulated security review.** `gitleaks`, `bandit -r`, `pip-audit`, `semgrep --config auto` (if network allows; else local rules), `bandit.yaml` honoured; **ZAP baseline** against the running prod-sim stack (`zap-baseline.py` in docker); manual OWASP checklist mapped to routes (authn/session/CSRF/tenant/IDOR/headers/cookies/upload/SSRF/error leakage); findings → issues → fixes → re-scan clean or waived-with-reason; `security-review-simulated.md` + signed evidence.
**7.4 (BLK-007) Simulated legal/privacy review.** `docs/legal/DPIA-lite-simulated.md` + `docs/legal/privacy-review-simulated.md`: RoPA (records of processing), lawful basis, minimisation, retention (30/90/365 buckets), DSR runbook (access/erase/export) **executed on synthetic subjects**, breach-notification tree, DPA template gap list, sub-processor list (none external; Ollama local). Signed by simulation authority; banner: not legal advice.
**7.5 (BLK-016/017) Un-quarantine + correctness harness.** Move the 19 UI tests into the suite (fix or delete-with-ADR); suite must pass with 0 deselected. **Engine correctness**: golden vectors file (WFM vs textbook Erlang C reference computed independently; RTA vs fixture ground truth; CX monotonicity; CRM totals vs manual; Personnel/B2B sanity), property-based tests (Hypothesis) for invariants (capacity ≥ load ⇒ SLA ≥ threshold; determinism; bounds), and a cross-check script comparing engine outputs to an independent minimal implementation for the 20 readiness calls; `engine-correctness-report.md`.
**7.6** `external_observer_audit` (Phase 5.2) executed and packed.

**Gate to proceed:** all simulated reviews green or findings closed; UI tier un-quarantined; correctness report committed.

### Phase 8 — Scale, soak, CI-wired evidence (1 day)

**8.1** **Soak**: 1,500-seat shape — `telemetry_simulator.py --agents 1500 --ticks 720` (or extend) against ingest; 6 h bounded; memory/CPU flat; no dropped ticks; latency p50/p95/p99 logged; ingest error rate = 0; report.
**8.2** **Fixture-scale readiness in CI**: add `.github/workflows/readiness.yml` (or extend ci.yml): checkout → venv → `HELIX_TENANT_DATA_DIR` (fixtures **not** in git; CI downloads from a seeded release asset or skips-with-notice on PRs) → run harness → upload evidence pack artifact; never fail a PR on fixture absence (skip + notice), always fail on harness failure.
**8.3** **Drift monitors**: `scripts/check_fixture_drift.py` — re-hash curated manifests weekly; alert on change; `scripts/check_claims_drift.py` — grep for forbidden claims ("PRODUCTION ready" without SIMULATED prefix; "certified"; "audited by") in docs; CI-enforces the vocabulary.
**8.4** **Consumer-risk caveats codified**: `docs/onboarding/consumer-caveats.md` — tickets 2.7% sample vs `queue_metrics_daily` authoritative; Cairo timezone; FK order; idempotent re-import; SLA projection windows; what a real client must confirm day-1.
**8.5** Performance re-run at fixture scale; compare vs 2026-10-31 baseline; flag regressions > 20%.

**Gate to proceed:** soak pass; CI wired; drift checks green; caveats written.

### Phase 9 — Claims, docs, activation runbook (½–1 day)

**9.1** **Disclosure-first docs flip**: README roadmap/status sections, `index.html` (status tag → "SIMULATED_PRODUCTION_READY — see SIMULATION_DISCLOSURE.md"), `docs/PRODUCTION_STATUS.md` (new section: what is proven, what is simulated, what remains), `MASTER_STORY.md`, `docs/KNOWN_ISSUES.md` (each closed item → FIXED+evidence; open items explicit), `RELEASE_NOTES.md`, `CHANGELOG.md`, portfolio docs, `docs/release/release-boundary.md` (add the simulated profile; keep the human-boundary for `PRODUCTION`).
**9.2** **SIMULATION_DISCLOSURE.md** (root): what simulation proves, what it cannot, the exact wording allowed in any external communication ("verified by simulation; real-client activation pending"), forbidden wordings, contact for the activation runbook.
**9.3** **Second-operator drill on docs** (BLK-024): clean-room person-follows-runbook test on the *documentation itself*; gaps → fix.
**9.4** **Activation runbook** `docs/release/REAL_CLIENT_ACTIVATION.md` — the "when reality arrives" checklist (target: ≤ 1 working day, zero code changes): (1) receive real exports → (2) run `scripts/production_readiness/run.py` with `HELIX_TENANT_DATA_DIR` → (3) import via App Phase-4 path → (4) re-run attack suite + drills → (5) real DPA/DPIA + legal sign-off → (6) real pen-test or waiver → (7) real `production_approved` sign-off by the client + human → (8) flip profile to `production` → (9) deploy prod-sim → production topology (swap Caddy internal CA for real CA; DNS; monitoring) → (10) 30-day hypercare. Each step lists owner role, command, evidence, and abort criteria.
**9.5** **Commit + tag** `v1.0.0-simulated` ; push; release notes; artifact attached (Phase 6.4); SHA256 manifest published in repo (not secrets).

**Gate to proceed:** docs consistent (claims-drift script green); tag pushed; runbook reviewed by clean-room pass.

### Phase 10 — Final verification gauntlet (½ day)

Run, in order, all on the tagged candidate; paste outputs to `docs/production_readiness/evidence/final-gauntlet-2026-11-…/`:

1. `python -m pytest -q` → **0 deselected**, all green; record counts/duration.
2. `ruff check .` → 0; `ruff format --check .` → clean; `python scripts/check_dependencies.py` → pass.
3. `python scripts/check_migration_drift.py` + `helix_codex_app/scripts/check_app_migration_drift.py` → no drift.
4. `python scripts/health_check.py` → READY.
5. Readiness harness → 12/12; evidence committed.
6. Tenant chaos acceptance → 24/24; fixture validation → 98/98 + 121/121.
7. App/API drill suite (128) → pass; **App CSV import e2e** (both tenants) → pass; screenshots.
8. Cross-tenant attack suite → 0 leaks; audit chain verifies.
9. DR drill ×3 → pass; RTO/RPO recorded.
10. Simulated observer audit → pass; `verify_simulation_signoff.py` → OK.
11. `python scripts/release_gate.py --profile simulated_production` → **`SIMULATED_PRODUCTION_READY`**, exit 0; and `--profile production` → **NOT_READY**, exit 1 (proof the boundary still holds).
12. ZAP baseline → no highs; all findings fixed/waived.
13. Claims-drift + fixture-drift checks → pass.
14. `git status` clean; tag exists; remote CI green (or documented).

**Definition of done:** all 14 green; the only unchecked boxes are the ones reality must fill (Phase 9.4).

---

## 3. Sequencing & parallelism

```
Phase 0 → Phase 1 → Phase 2 ─┬─ Phase 3 ── Phase 4 ─┐
                             └──────────────→ Phase 5 ─┼─ Phase 6 ─┐
                               Phase 2 ─────→ Phase 7 ─┘           ├─ Phase 9 → Phase 10
                                              Phase 8 ─────────────┘
```

- 3 and 5 are independent (isolation vs approval architecture) and may run in parallel by two agents; merge via the Phase-0 branch with rebase, never force-push.
- 6 needs 5 (signoff) for its artifact; 7 needs 6 running for ZAP; 9 needs everything; 10 is serial.
- Any phase failing twice → stop, root-cause, ADR if design changes; do not stack workarounds.

## 4. Effort & risk

| Phase | Effort | Main risk | Mitigation |
|---|---|---|---|
| 0–1 | 1 d | hidden suite/CI failures surface | fix-forward with pinning tests |
| 2 | 1–2 d | dispatch/connector behavior change breaks callers | contract tests first; ADR for removals |
| 3 | 1 d | migration on existing DBs | backup first; drift checks; rollback tested |
| 4 | 1 d | CSV edge cases eat time | curated layer only; hard limits; quarantine |
| 5 | 1–2 d | profile semantics drift | gate tests pinned before wiring |
| 6–7 | 2–3 d | docker/ZAP flakiness, time | fallback: static analysis + manual checklist, disclosed as such |
| 8 | 1 d | fixture absence in CI | skip-with-notice; artifact from owner machine |
| 9–10 | 1–1.5 d | claims drift re-creep | CI check; single editor for status docs |

**Total: ~8–10 working days** of focused agent execution, zero owner time, zero external dependency.

## 5. What this plan deliberately does not do

- Emit `PRODUCTION`, `certified`, `audited by`, or any human-authority wording.
- Touch `00_CONSTITUTION.md` or weaken fail-closed gates.
- Delete the 19 UI tests (fix or justify, never silently drop).
- Upload anything to external services; all evidence stays local; no pushes before Phase 10 sign-off of the branch.
- Claim real-client readiness; it claims **simulated production readiness + a proven activation path**.
