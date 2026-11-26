# GOVERNANCE.md — Operating Policy & Repo Map for Helix-Codex

> Companion to `CONSTITUTION.md` (the *why* — philosophy and clean-code policy, which
> this file enforces operationally) and `AGENTS.md` (the agent charter + ledger).
> Read all three before acting. This file may be updated by any agent **as a logged
> governance change** to keep the map and policy truthful; the CONSTITUTION itself is
> owner-only.

## 1. Repository map

Authoritative directory map for **Helix-Codex** (the Helix Prime operations core).
Any file you add, move, rename, or delete gets reflected here in the same landing.

| Path | What it is |
|---|---|
| `CONSTITUTION.md` | The owner's unified engineering philosophy & clean-code policy (root, owner-only text). |
| `AGENTS.md` / `GOVERNANCE.md` | Agent charter + ledger / this operating policy. |
| `README.md` | Single source of truth (house style; carries docs-sync + generated role-matrix blocks). |
| `SHIPMENT_READINESS.md` | The status file: full evidence record, the nine red production gates. Stays at root. |
| `CHANGELOG.md`, `LICENSE.md`, `SECURITY.md`, `requirements.txt`, `requirements-dev.txt` | Standard root set. |
| `index.html` | House-style landing page (mirrors the README). |
| `_docs_profile.json` | Facts + status templates for the `docs-sync` CI engine (kept at root; engine reads it there). |
| `docs/` | Living reference: `PRODUCTION_STATUS.md`, `PROJECT_ARCHITECTURE.md`, `SYSTEM_ARCHITECTURE.md`, `PRODUCT_DEFINITION.md`, `COMMERCIAL_STORY.md`, `DOCUMENTATION_STATUS.md`, `MASTER_STORY.md` (verified-reality record), `HELIX_CODEX_OS_MASTER_BLUEPRINT.md` (architecture authority), `architecture/`, `portfolio/`, `release/`, `operations/`, `legal/`, `verification/`, `onboarding/`. |
| `docs/archive/` | Historical: superseded constitutions, old AGENTS ledgers, one-off plans, dated audits. Archive, never delete. |
| `GOVERNANCE/` | Operational policy, gates, capability matrix, audit log, and `governance_check.py` (a governed subsystem of the app — not root docs). |
| `helix_codex_app/` | The governed FastAPI core (`helix-api`): identity, RBAC, workflow engine, calendar, governed memory, audit ledger. |
| `engines/` | The six business engines (WFM/Erlang C, RTA, CX, B2B, Personnel, CRM) and shared math. |
| `control_plane/` | Governance control plane (`governance.py` role catalog, kill switch, gate surface). |
| `capabilities/` | Versioned capability packs; `capabilities/restaurant/` is the reference pattern. |
| `server/`, `connectors/` | API server assembly and read-only connectors (Zendesk, Salesforce, Clay). |
| `organization/`, `contracts/`, `memory/`, `metacognition/` | Role catalog YAML, published contracts, governed memory, metacognition store. |
| `release/`, `evidence/` | Release tooling, signed evidence packs, drift/DR/soak checks. |
| `pilot/`, `customer_success/`, `observability/`, `orchestration/`, `infra/`, `cloud/`, `deploy/` | Simulated-production topology, CS surfaces, observability, deploy assets. |
| `cockpit/`, `cockpit_ui.py`, `supervisor.py`, `telemetry_simulator.py`, `ingest_engine.py` | Helix Ops Cockpit (out-of-band diagnostic tooling; not part of the governed-core gate surface). |
| `mock_server/`, `demo/`, `integrations/`, `ops/` | Synthetic mock server, demo content, integrations, ops scripts. |
| `tests/` | The test suite (CI runs `-m "not smoke"` with coverage floors; `tests/integration/ui/cockpit/` is the deselected UI tier). |
| `src-tauri/`, `icons/`, `config-files/`, `.streamlit/` | Desktop shell, assets, configs. |
| `launch.py`, `launch.bat`, `setup.sh`, `setup.bat`, `run_tests.ps1` | Run/setup helpers. |

## 2. Documentation policy (what belongs where)

**Root holds only the requested set** — nothing else:

| File | State | Purpose |
|---|---|---|
| `README.md` | required | The single source of truth: what this is, why it's here, how to use it — in simple English for a professional reader. Carries the Helix Solutions logo. |
| `AGENTS.md` | required | Agent charter + sign-in/out ledger. |
| `CONSTITUTION.md` | required | The owner's engineering philosophy and clean-code policy (unified across every repo). |
| `GOVERNANCE.md` | required | This file: repo map, documentation policy, sync policy, archiving rules. |
| `CHANGELOG.md` | standard | Dated user-visible changes. |
| `LICENSE` / `LICENSE.md` | standard | MIT, unless the repo states otherwise. |
| `SECURITY.md` | standard | Threat model, vulnerability reporting, secret handling. |
| `SHIPMENT_READINESS.md` | status file | The honest, dated evidence record and gate table. Must stay at root. |

**Everything else lives in `docs/`** — reports, audit logs, execution plans, research
notes, ADRs, runbooks, anything dated or one-off. No stray `.md`/`.txt` at the root.
If a document at the root is not in the table above, move it to `docs/` (or
`docs/archive/` if it is historical) and record the move in the `AGENTS.md` ledger.

## 3. Synchronization & harmony policy

The owner's rule: **the repository's actual status must match its README at all times,
locally and remotely.**

1. `README.md` is the canonical account. Landing pages (`index.html`) and dashboards
   mirror it; they never fork it.
2. When reality changes, update `README.md` **first**, then mirror it to the pages.
3. Every sanctioned change is committed **and pushed** to the default branch, so the
   GitHub copy, the local working copy, and any local platform that reads the repo
   all show the same truth.
4. A number published anywhere (README, page, badge) must be reproducible from this
   repository. A stale figure is removed, not left to rot.
5. The workspace tool `readme-sync/` (in `Repos_Readmes`) verifies that every public
   repo's README matches its local clone. Keep this repo's README in a state it reports
   as matching.
6. The `docs-sync` CI engine (`.github/workflows/docs-sync.yml`, on release publish)
   rewrites the `docs-sync:start/end` status block in `README.md` and `index.html`
   from `_docs_profile.json`. Keep those markers and the profile's facts current; never
   hand-edit a synced block to disagree with `_docs_profile.json`.

## 4. Archiving rule

- Archive (move to `docs/archive/`), never delete: historical reports, superseded plans,
  dated audits, and one-off execution logs.
- Delete outright only regenerable artifacts: caches, build output, coverage files.
- Record every move in the `AGENTS.md` ledger with date and time.

## 5. Engineering philosophy & clean-code policy (operational summary)

The full text is `CONSTITUTION.md`. The operational reminders, enforced here:

- **Fail closed.** Missing input or missing authority is a refusal, never a default.
- **Evidence before claims.** Published numbers carry a command, a date, and an artifact.
- **No duplicates, no temp files, one file one job, every file explains itself.**
- **Secrets never enter the tree.**
- **Simple English** in code, docs, and UI, so a non-technical professional reader
  (recruiter, partner) can follow.
- **One brand mark:** the Helix Solutions logo, everywhere.

## 6. Definition of done

It works; it has a test or a documented manual check; the `AGENTS.md` ledger has an
entry; the docs reflect the new reality; no temporary file was left behind; and every
published number can be re-run to reproduce itself.
