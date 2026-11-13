<!-- AGENTS.md is now a concise orientation. The full historical build ledger
     (all COMPLETE step ledgers, sections §1..§N, ~5,600 lines) lives in
     AGENTS.details.md — moved there for ME-12 to keep this file lean. -->
# AGENTS.md — Helix Codex OS Build Ledger

> **Purpose:** Any agent (or human) can pick up exactly where the last one stopped.
> **Current status (2026-10-31):** the local full suite reported 2,000 passed and
> 19 deselected; fixture/engine readiness passed 12/12 gates; the App/API operations
> drill and simulated design-partner drill passed their defined scopes. See §27–§28.
> This is local simulated evidence, not a real customer pilot, independent review, or
> production approval. Production remains `NOT_READY`.
>
> The §20 B-, A- and follow-up sections are CLOSED — §20.30 carries their historical
> closure table and commit SHAs. The earlier 1,897-test result recorded there is a
> dated baseline, not the current suite total. The
> §22.1 adapter findings are also CLOSED — **§22.4 carries the 2026-09-30 closure
> batch: all six adapters now drive a real computation end-to-end.** §23
> (ERLANGC-1) is CLOSED — the WFM Erlang C engine was rewritten on the textbook
> Erlang B recursion (`caabcb9`), pinned by 42 reference tests (`0f8c4a1`), and
> the README/KNOWN_ISSUES claims were aligned to it (`6f57d74`, `e32a0ca`, and
> the §23.6 commit); §23.7 carries the step table. §18 (GOV-1) is marked IN
> PROGRESS above only because of the owner-driven item below; its engineering
> work is complete, and §18.10 closed its last open item.
>
> §18.9 closed a systemic leak worth keeping in view: all eleven
> `tempfile.mkdtemp` sites in the release path route through
> `release/scratch.py`, and the Windows bulk-delete guard was finally explained
> (§18.4) — **pytest always deletes via a `\\?\` path, so the guard's temp-dir
> exemption never applies; raise `CODEBUDDY_SAFE_DELETE_BULK_THRESHOLD` for any
> broad run.**
>
> What remains is owner-driven: Phase 6 (B2–B4) — infrastructure spend, paid
> external parties, and legal/human authority. **No code change can unblock
> Phase 6** — the nine production-only gates need signatures from keys held
> outside this repository.
>
> This local checkout currently has no configured Git remote. Its current online
> publication state is not asserted here. The bounded push authorization recorded
> below expired on 2026-10-15 and does not authorize a push now.
>
> **Historical repository observations — not current measurements:** on 2026-09-29
> `main` was level with `origin/main` at `1830f30`; on 2026-09-25 the GitHub API
> reported the repository public and the owner confirmed that visibility was intended.
> These historical facts do not establish the current online state. This checkout has
> no remote configured; do not infer a current backlog or visibility from the old rows.
> If a remote is restored, re-measure with `git ls-remote` and compare against the
> current local commit before making a publication claim.
>
> **First all-steps-green CI result — 2026-09-29 (historical).** Run
> [`36497766876`](https://github.com/<YOUR_GITHUB_ORG>/Helix-Prime/actions/runs/36497766876)
> on `839507e` passed **all 17 steps**: `1,897 passed, 19 deselected`, coverage
> 86.91%. The workflow had failed at **step 5 on every push from 2026-09-20 to
> 2026-09-28**, which is why steps 6–17 had never executed once and why several
> pre-existing defects were invisible. Full record: §21.
>
> The latest remote-CI measurement recorded in this repository is later: 2026-10-05,
> run `37371376357`, **1,967 passed / 19 deselected**, coverage 86.91%. Neither
> historical run is a CI result for the 2026-10-31 local source tree.
>
> **Pushes are gated on explicit human authorization.** Commits inside the
> workspace follow the standing authorization; pushes do not. The backlog was
> pushed on 2026-09-27 under explicit authorization (`6b7d923..1c8c19d`), and
> §21's three commits were pushed on 2026-09-29 under the owner's instruction to
> repair the workflow. Any commit after those needs its own authorization.
> **Standing push authorization — bounded, granted 2026-10-01.** Scope: this
> repository only; branch `main` only; fast-forward pushes only. Covered:
> documentation, tests, bug fixes, and commits following a task the owner has
> assigned in the session. **Not covered — each needs the owner's explicit
> approval for that action:** force-push or history rewrite; creating or moving
> tags or releases; changes to dependencies or lockfiles; changes to
> `.github/workflows` or CI triggers; changes to repo settings, visibility,
> branch protection or pins; deleting branches; anything under the Phase 6
> production-only gates. **Condition:** before each push, every step in
> `.github/workflows/ci.yml` (job `check`) must pass — meaning those exact
> commands run locally, in order — or the last CI run on `main` must be green
> for the same commit's parent. The steps, named exactly as in the file:
> `Set up Python ${{ matrix.python-version }}`; `Install dependencies`;
> `Run ruff (linting)`; `Run ruff format check`; `Run mypy (type checking)`;
> `Run test suite`; `Run security scans`; `Check dependencies`;
> `Check migration drift (store schema vs alembic head)`;
> `Check governance catalog drift (runtime catalog vs role-catalog.yaml)`;
> `Check capability registry mirrors are current`;
> `Check governance authority (constitution + doc authority chain)`;
> `Build package`; `Validate API container definition`;
> `Smoke test API container readiness`. After each push, poll the public
> Actions API for the run on the pushed SHA and report every job's conclusion
> — if any job is red, stop and report; do not fix forward without asking.
> **Expiry:** this grant lapses on **2026-10-15** unless the owner renews it.
> It does not apply to any other repository. Any change to this note, to the
> push rules in `AGENTS.md`, or to the expiry date requires the owner's
> explicit approval for that change; this grant never covers editing itself.
>
> Everything else is COMPLETE history: §1 (Production Hardening, H0–H3), §1A (app
> UI modernization, UI-1), the sports-academy pack (S0–S7), §2–§19, and §20
> (PORTFOLIO-DOCS-1) with its B-, A- and follow-up sections. Do not restart
> completed sections. Read the current status above and §27–§28 first; §20.30 is a
> historical closure table. Update this file immediately after
> completing each step.
>
> **Out-of-band tooling (§19):** four standalone modules at the repository root —
> `telemetry_simulator.py`, `ingest_engine.py`, `supervisor.py`, `cockpit_ui.py` —
> form the Helix Ops Cockpit. They are **not** part of the governed core: nothing
> under `tests/` imports them, they are absent from `release/release-manifest.json`,
> and they appear in no gate profile. They do not change the governed-core gate
> surface or the 2,000-test current local baseline. Their own coverage lives in a quarantined
> integration tier — `tests/integration/ui/cockpit/`, 19 tests, deselected by
> default; run it with `pytest tests/integration/ui/cockpit/ -m ui_integration`.

---

## 0. Project context (read first)

> **Authority chain:** `00_CONSTITUTION.md` (authority) →
> `docs/HELIX_CODEX_OS_MASTER_BLUEPRINT.md` (architecture + commercial record) →
> implementation. `MASTER_STORY.md`, `ROADMAP.md`, `CHANGELOG.md`, and `docs/`
> status summaries are subordinate records — they never outrank the constitution
> or the blueprint, and they are replaced/archived as they stale.
>
> **This file is the single authoritative status surface.** `helix_codex_app/agents.md`
> is a subordinate record: it keeps the app's own phase history, design rationale,
> constraints, and dated baselines, and it asserts no current status of its own. If the
> two ever disagree about what is done, this file is right and the other is stale. See
> §20.12 for how that was resolved.

- **Repo:** Helix-Prime repository root. `E:\Helix-Prime` is the historical Windows path.
- **Mission:** maintain the local-first governed operations core and its synthetic
  capability prototypes. The sports-academy pack is a prototype for an opportunity
  scenario; Scoach Academy Hub is not a confirmed partner or client. Background
  hypothesis: `docs/scoach_academy_hub_opportunity_report.md`.
- **Blueprint:** `docs/HELIX_CODEX_OS_MASTER_BLUEPRINT.md` (governs architecture).
- **Constitution:** `00_CONSTITUTION.md` wins over any doc on conflict.
- **Python:** 3.12 canonical. The workspace test environment is `../../.venvs/helix-prime`.
- **Test command:** `python -m pytest tests/ -q -m "not smoke"` (run from this repo root).
- **Lint:** `ruff check <paths>`.

### Non-negotiable rules (violating these breaks the governed core)

1. **Reference pack:** `capabilities/restaurant/` is THE pattern. Copy its shape,
   never invent a new one.
2. **Never edit** `organization/role-catalog.yaml`, `control_plane/governance.py`
   (ORGANIZATION_CATALOG), or `organization/capability-registry.yaml` + mirrors for
   this pack. Roles stay pack-local. Engines are reused via existing capability ids.
3. **Data discipline:** pack runs `DATA_MODE = "simulated_realistic"`, read-only
   connectors, no live writes, `production_readiness = "NOT_ESTABLISHED"`.
4. **Every governed-memory record** carries: tenant_id, client_id, provenance
   (correlation_id, data_mode, basis, sources), evidence_refs, classification.
5. **No comments in code** unless they mirror the restaurant pack's docstrings
   (module docstrings ARE kept).
6. **Each step must end with:** tests passing at ≥ baseline + ruff clean on new
   files + this file updated + commit made (see git protocol below).

### Git protocol

- User has authorized commits for this work. Commit after EVERY completed step.
- Style: `feat(academy): <what>` / `test(academy): <what>` / `docs: <what>`.
- NEVER `git add -A` blindly; stage only files you touched. NEVER commit
  `.db` files, `__pycache__`, or `.venv*`.

---


## Full build ledger (historical)

The detailed, dated step ledgers and completion records (sections §1 through §N)
have been moved to **AGENTS.details.md** to keep this orientation file lean.
Read AGENTS.details.md for the complete history a resuming agent needs.
