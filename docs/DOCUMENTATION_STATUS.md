# Documentation status and source of truth

**Reconciled:** 2026-10-31  
**Project:** Helix-Prime

This repository contains current guides, dated verification reports, historical
handoffs, design plans, and marketing drafts. They do not all describe the same date
or evidence class. Use the documents below for current state; treat dated records as
snapshots, not as claims about the present checkout.

The 2026-10-31 reconciliation inventoried all 142 tracked or non-ignored Markdown
documents in the repository; generated cache files are excluded. Current-facing claims
were reconciled; dated evidence and historical records remain dated rather than being
rewritten as new verification.

## Current authoritative status

- [`PRODUCTION_STATUS.md`](PRODUCTION_STATUS.md) — current release boundary, tested
  local scope, limitations, and next actions.
- [`../README.md`](../README.md) — project overview and concise current verification
  snapshot.
- [`../AGENTS.md`](../AGENTS.md) — implementation ledger and detailed current run
  evidence (§27–§28).
- [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) — current open limitations and explicitly
  marked historical defect records.
- [`../ROADMAP.md`](../ROADMAP.md) — next work, with the local simulation distinguished
  from a real pilot.
- [`production_readiness/simulated-design-partner-drill-2026-10-31.md`](production_readiness/simulated-design-partner-drill-2026-10-31.md)
  — scope/results/boundaries of the local synthetic drill.
- [`release/app-tenant-ops-drill-2026-10-31.md`](release/app-tenant-ops-drill-2026-10-31.md)
  — App/API tenant isolation and operations rehearsal.
- [`portfolio/15_verified_test_results.md`](portfolio/15_verified_test_results.md)
  — current test snapshot followed by dated historical test tables.

## Current verified position

- Full local test suite: **2,000 passed, 19 deselected** (Python 3.12).
- Synthetic fixture/engine readiness: **12/12 gates**, 20 calls across six engines,
  two synthetic tenants, zero engine errors.
- Tenant fidelity: **24/24 acceptance checks**.
- App/API tenant and operations drill: passed; focused test set **128 passed**.
- Simulated design-partner drill: `PASS_SIMULATED`, **14/14 combined checks**.
- The production profile remains **`NOT_READY`**; nine production-only gates remain
  open. No real customer pilot, production deployment, external audit, legal review,
  or certification is recorded.
- The App has no CSV upload endpoint. Synthetic raw exports were ingested by the
  readiness harness; App HTTP checks used source-derived document/task workflows.
- The simulated reviewer checks are deterministic assertions, not separate LLM
  opinions or independent audit/legal evidence.
- Changed-path Ruff checks passed; repository-wide Ruff still has **21 existing
  findings** and **346 files needing format**.
- No remote is configured in the current local checkout; current online publication
  state and remote CI status are not asserted.

## How to read the rest of the documentation

1. **Dated evidence remains immutable.** Files under `docs/verification/`,
   `docs/production_readiness/evidence/`, `docs/audits/`, and `docs/release/handoff/`
   record the conditions and output of their named runs. Do not edit old results to
   make them look current; add a new dated record instead.
2. **Plans and proposals are not commitments.** The Scoach opportunity report, pilot
   templates, master plans, commercial stories, and pricing drafts describe hypotheses
   or intended designs. No actual partner, approved offer, or customer data is implied.
3. **Historical project ledgers are not current status pages.** `MASTER_STORY.md`,
   `AGENTS.md`, `GOVERNANCE/WORKSPACE_MAP.md`, and subordinate app ledgers contain
   dated history. Their current summaries point to the source documents listed above.
4. **Generated evidence is not a release label.** `PRODUCTION_READINESS_EVIDENCED`
   describes the synthetic readiness harness only. It does not satisfy the C8
   production profile or certify the product.

## Change record

The 2026-10-31 documentation reconciliation updated current-facing status and claims
across the README, roadmap, changelog, production status, known issues, portfolio
summaries, case/commercial material, sports-academy opportunity documents, operational
guides, architecture/status summaries, and governance maps. Historical run artifacts
and dated audit narratives were preserved rather than rewritten. No code, release
classification, or external evidence was changed by this documentation update.
