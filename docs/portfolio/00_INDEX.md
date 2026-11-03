# Helix Codex — Project Portfolio & Release Evidence Package

**Positioning (design intent, realized by demonstrated mechanisms):**

> An accountable AI operating organization that understands business context,
> coordinates governed workflows, remembers decisions and outcomes, and improves
> through evidence without silently taking control.

This package is a **portfolio/review artifact**. Every claim below is tied to code
that exists in this repository and tests that pass. The narrative claims only what has
been demonstrated; unfinished items are listed separately in
[`11_known_limitations.md`](11_known_limitations.md) and
[`14_technical_decision_log.md`](14_technical_decision_log.md).

## What is demonstrated (completed)
- A governed core: identity, tenant isolation, governance, read-only connectors,
  workflow state machine, manual approvals with separation of duties, evidence/
  provenance, append-only memory, metrics, and an evidence-gated metacognitive
  improvement engine that **never auto-deploys**.
- A simulated two-tenant design-partner drill, run 2026-10-31, using synthetic chaos
  fixtures and the real local App HTTP routes. It passed 14/14 combined checks and
  exercises tenant-scoped summaries/tasks, but is not a real design-partner pilot.
- A read-only-first pilot package with consent, minimum-data, tenant-isolation,
  retention, rollback, and evidence controls. No real customer pilot has run.
- A first business capability pack (small restaurant) that **reuses the same core** and
  starts read-only with synthetic data.
- A second capability pack (**sports academy**), built with synthetic data for a
  sports-academy target scenario associated with Scoach Academy Hub (not a customer
  implementation), reusing the
  same core, with its own ontology, roles, KPIs and a read-only phase behind SOD approval.
- A governed FastAPI spine (**`helix-api`**, `server/`) as the canonical entry point:
  loopback-bound, auth-protected, with a kill switch and authenticated metrics.
- A synthetic demonstration running both a call-centre tenant and a restaurant tenant in
  **one governed memory** with tenant isolation and an intact audit chain.

## Verification summary (reproducible)

The current local snapshot was verified **2026-10-31**. Historical CI and earlier
repository measurements remain dated records; do not treat them as current local
source results. Every command below is reproducible; the dated earlier runs are kept as the audit trail in
[`15_verified_test_results.md`](15_verified_test_results.md).

- **Tests:** **2,000 passed / 19 deselected** in the local Python 3.12 run. The quarantined
  cockpit UI tier is excluded. Historical suite counts remain in
  [`15_verified_test_results.md`](15_verified_test_results.md).
- **Fixture / engine readiness:** 12/12 gates and 20 calls across six engines and two
  synthetic tenants; zero engine errors. Tenant-fidelity acceptance: 24/24.
- **App / API:** local tenant and operations drill passed; focused test set 128 passed.
  The simulated design-partner drill passed 14/14 combined checks.
- **Lint / format:** changed paths passed Ruff. Repository-wide status is not clean:
  the current record reports 21 existing Ruff findings and 346 files needing format.
  Do not repeat earlier 86.91% coverage or all-17-step CI results as measurements of
  this local source snapshot; those are historical CI records.
- **Governance:** `python3 -m GOVERNANCE.governance_check check` → `governance=PASS`.
- **Security:** the earlier `release.security_gate.run_security_gate()` result was
  `all_ok=True` — 0 secret
  findings, canonical classification set, deny-by-default, redaction, typed malformed-output
  handling, audit integrity.
- **Synthetic demo (clean setup):** the 2026-09-29 run exited 0 with 41 governed
  records across two tenants, intact audit chain, zero live-customer records, and no
  external writes; this is a dated historical measurement.
- **Release gates:** the 2026-10-31 non-writing C8 run returned
  `controlled_pilot` → `CONTROLLED_PILOT_READY` and `production` → `NOT_READY`; the
  nine production-only gates remain red. The broader 2026-09-29 profile set
  (`app_pilot`, `controlled_pilot`, `production_candidate`, `production`) is historical.

## Documents in this package

**Evidence documents (1–15)** — what is built and measured.

1. [Architecture overview](01_architecture_overview.md)
2. [Governance model](02_governance_model.md)
3. [Workflow demonstration](03_workflow_demonstration.md)
4. [Security model](04_security_model.md)
5. [Evidence model](05_evidence_model.md)
6. [Memory model](06_memory_model.md)
7. [Metacognitive improvement model](07_metacognitive_improvement_model.md)
8. [Local/cloud deployment strategy](08_local_cloud_deployment.md)
9. [Cost assumptions](09_cost_assumptions.md)
10. [Pilot plan](10_pilot_plan.md)
11. [Known limitations](11_known_limitations.md)
12. [Roadmap](12_roadmap.md)
13. [Five-minute demo script](13_five_minute_demo_script.md)
14. [Technical decision log](14_technical_decision_log.md)
15. [Verified test results](15_verified_test_results.md)

**Strategy documents (16–17)** — external and commercial planning, not evidence about the
code. Both are dated and neither is a claim about this repository's state.

16. [Market research, strategic sprint plan & career/financial roadmap](16_market_research_strategy_roadmap.md) — prepared 2026-08-29; superseded in part by 17
17. [Revised strategy plan — superseded](17_revised_strategy_plan.md) — the personal career assumptions in 16 are no longer current

**Supplement (added 2026-10-05, unnumbered).** Not part of the 1–17 sequence above;
numbering is referenced elsewhere in the repository and is not renumbered for an
append.

- [Engine-to-skill map](ENGINE_TO_SKILL_MAP.md) — what each of the six engines is,
  beside the market skill it evidences. Engine names, invoked source modules,
  implementation size and test-module counts are measured from the tree at the
  commit named in the document; the market-skill column is editorial and labelled
  as such. Claims no pass rate, coverage, or CI status. Regenerate with
  `career_automation/engine_to_skill_map.py`.

## Status (2026-10-31)
- **Pilot package / controlled-pilot profile:** locally gate-ready; not evidence of a real pilot.
- **Simulated design-partner drill:** `PASS_SIMULATED`, 14/14 checks; synthetic only.
- **Real design-partner approval or participation:** none recorded.
- **First customer deployment:** not ready; production profile remains `NOT_READY`.
- **Production readiness:** **NOT_ESTABLISHED**; nine production-only gates still require genuine external evidence and human authority.
