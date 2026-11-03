# Helix Prime — Roadmap

> **Classification:** PROJECT DOCUMENT
> **Rule:** No claim in this document may exceed what is verified in `MASTER_STORY.md`. This roadmap is replaced by this file when the previous draft is found to contradict verified reality. See `CHANGELOG.md` for the audit trail.

---

## Where the project actually stands

Helix Prime is a local-first governed operations platform. The local C8 profile returns
`CONTROLLED_PILOT_READY`; this is an internal gate classification, not evidence that a
real customer pilot has occurred. The 2026-10-31 simulated design-partner and App/API
operations drills passed their stated scopes. There are still no recorded customer
deployments, production usage, or verified revenue.

**What is real today (verified):**

- 6 business engines: WFM/Erlang C, RTA, CX Churn Sentinel, B2B Onboarding, Personnel, CRM
- 9 AI agents: SAMI, SUBY, PHILI, WILI, ANDY (Compliance & Quality), NONO (Fraud), MAYA (Marketing), LIZA (Sales), TOMY (ICT), connected to a local Ollama model
- An orchestrator with content-based request routing
- **`helix-api`** — the governed FastAPI spine (`127.0.0.1:8000`), the one deployable artifact: identity, RBAC, approvals, kill switch, metrics, audit chain. The Streamlit cockpit is now a **read-only secondary diagnostic surface**.
- **Helix Codex App** — the first daily-use product layer (`helix_codex_app/`): identity, chat, documents, tasks, calendar, attendance, governed memory, and a low-code capability loader
- **2 vertical capability packs**: `capabilities/restaurant/` (the reference pattern) and `capabilities/sports_academy/` (a sports-academy prototype built with synthetic data; Scoach Academy Hub is an opportunity target, not a confirmed partner)
- **C8 release gate** — `release/gate.py`, 29 gate implementations (14 core + 6 app + 9 production-only) across 5 named profiles
- A local repository checkout; no Git remote is configured here and current online visibility is not asserted
- **Local verification (2026-10-31)** — the full suite reported **2,000 passed, 19 deselected**; fresh fixture/engine readiness passed **12/12 gates** across **20 calls**; the two-tenant simulated design-partner drill passed **14/14 checks**; and the App/API tenant and operations drill passed its focused controls. See [`docs/PRODUCTION_STATUS.md`](docs/PRODUCTION_STATUS.md) and [`AGENTS.md`](AGENTS.md). These are local results, not a current remote CI run or a production claim.
- **Historical CI** — the latest recorded remote run is dated 2026-10-05 (1,967 passed,
  19 deselected; coverage 86.91%). It is not evidence for the 2026-10-31 local source
  state.

**What is explicitly NOT real yet — do not claim otherwise:**

- No client deployments and no production enterprise usage
- No real-client pilot has run; the 2026-10-31 design-partner drill used only synthetic fixtures
- No revenue, no pricing model, no budget of a team that does not exist
- No certifications: no SOC 2, no ISO, no independent audit
- The 9 production-only gates remain red by design — they require external humans, external auditors, and legal review that do not exist
- No patent filings, no blockchain integration, no quantum-computing work

The control-plane `audit_events` ledger is append-only and hash-chained; it is implemented and exportable through `scripts/export_evidence_pack.py`. It is a local evidence mechanism, not a claim of production certification.

---

## Working agreements

This is a **one-person** effort. Everything below is sized for that reality.

1. **Truth over appearance** — a feature is "done" only when it has been run and observed in this session. A plan is a plan until it is executed.
2. **Filesystem over summary** — verify claims with commands, not with descriptions.
3. **Small, honest increments** — one working improvement shipped is worth more than a roadmap of promises.
4. **Anything fabricated is removed** — documents that overstate the project are corrected the same week they are found.

---

## Now (current focus)

1. **Decide whether an App CSV import is required.** The current harness ingests synthetic exports; the App drill used its real HTTP document/task routes. There is no App CSV upload workflow. Implement and test a tenant-scoped import path only if that is part of the intended product scope.
2. **If a real pilot is pursued, make it a separate owner-authorized activity.** The simulated drill is not a real Scoach Academy Hub engagement. A real pilot requires an actual participant, explicit consent, a named operator, a bounded data scope, and operational safeguards.
3. **Keep the external production gap explicit.** The nine production-only gates still need genuine outside evidence and human authority; local simulation cannot satisfy or waive them. See [`docs/release/production-blockers.md`](docs/release/production-blockers.md).

## Next (once the above is stable)

1. ~~**Demo assets**~~ — **resolved 2026-09-29.** The stale render was withdrawn
   from the distribution path: removed from the working tree (quarantined at
   `E:/_quarantine_2026-09-29/`) and excluded from both the Azure bundle
   (`marketing/azure.yaml`) and the Docker build context (`marketing/.dockerignore`).
   `index.html` never referenced it. This item previously said the `.vtt` also
   carried the retracted narration — **it did not**; the captions were regenerated
   from the corrected script in `c5a88ef` and are current. Closes issue #3. See
   `CHANGELOG.md`.
2. **Close repository-wide lint/format debt** — the current local record reports 21 existing Ruff findings and 346 files needing formatting; changed paths are clean.
3. **Re-run complete CI-equivalent validation** on the exact candidate source and preserve the resulting artifact set before any release decision.
4. **Decide the public product name** — the repository says Helix Prime, the commercial layer says Helix Codex OS, and the manifest says Helix-Prime-Codex.

## Not on the roadmap

- No marketing of features that do not run yet.
- No invented team structure, budgets, or revenue targets.
- No fabricated customer names or "accounts exercised."

---

## Contact

Helix Prime is built and maintained by Hatem Shalaby. Public contact is via the GitHub profile: `github.com/<YOUR_GITHUB_ORG>`.

*Any email addresses ending in `helixprime.io` found in older versions of this repository are fabricated and void.*

<!-- HELIX_ROLE_MATRIX:START -->
## Canonical RoleSpec matrix (generated)

This block is generated from `control_plane/governance.py`. Role IDs,
engine ownership, data classifications, approval limits and KPIs below
are structural facts; surrounding prose must not contradict them.

| RoleSpec ID | Engines | Classifications | Financial limit (USD) | KPIs | Oversight only |
|---|---|---|---:|---|---|
| `sami` | wfm, rta, cx, crm, b2b, personnel, control_plane | public, internal, client_confidential, personnel_sensitive, financial, regulated_high_risk | unlimited (human escalation) | system_health, operational_margin | False |
| `ops_gm` | wfm, rta, cx | internal, client_confidential | 500.00 | sla, service_level, occupancy, adherence, aht | False |
| `compliance_quality_gm` | none | public, internal, client_confidential, personnel_sensitive, financial, regulated_high_risk | 0.00 | quality_score, compliance_drift | True |
| `fraud_revenue_gm` | crm, b2b | internal, client_confidential, financial | 0.00 | leakage, anomaly_delta | False |
| `hr_personnel_gm` | personnel, wfm | internal, personnel_sensitive | 1000.00 | turnover_rate, time_to_hire | False |
| `ld_gm` | wfm | internal, personnel_sensitive | 200.00 | competency_score, time_to_competency | False |
| `sales_gm` | crm, b2b | internal, client_confidential | 2500.00 | pipeline_value, win_rate | False |
| `marketing_gm` | crm | public, internal | 500.00 | cac, lead_volume | False |
| `ict_gm` | control_plane | internal, regulated_high_risk | 5000.00 | engine_latency, model_timeout | False |

### Runtime aliases

| Alias | Canonical role / engine |
|---|---|
| `SAMI` / `sami` | `sami` |
| `SUBY` / `suby` | `ops_gm` |
| `PHILI` / `phili` | `hr_personnel_gm` |
| `WILI` / `wili` | `ld_gm` |
| `NONO` / `nono` | `fraud_revenue_gm` |
| `fraud_gm` (YAML compatibility alias) | `fraud_revenue_gm` |

### Limitations

- `None` financial limit does not mean autonomous unlimited approval; SAMI remains human-escalated.
- `oversight_only=True` means the role proposes/reviews and does not execute an engine.
- Unknown role, engine, classification or alias fails closed.
- This matrix is not a production certification or customer deployment claim.
<!-- HELIX_ROLE_MATRIX:END -->
