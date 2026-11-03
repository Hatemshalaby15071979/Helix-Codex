# Case study — Helix Prime

**data_mode: "simulated_realistic".** Every number below is a measurement on synthetic
data or a reading of source. There is no real design partner or customer traffic. A
two-tenant simulated design-partner drill passed locally on 2026-10-31; it is not a
customer engagement, independent audit, or legal review.

**Positioning (2026-10-31).** Locally verified, governed operations core with six
engines exercised on synthetic tenant fixtures, plus App/API tenant and operations
drills. The current local test run reported 2,000 passed and 19 deselected. The
production profile remains `NOT_READY`; nine production-only gates still require
external evidence and human authority.

## The problem

An operations core that can execute actions on a live floor — staffing changes, CRM
writes, personnel moves — has one job that matters: never run an action the acting role
is not allowed to run, and never run one it should not run without a human in the loop.
On a real floor, a wrong automated action is an SLA or compliance breach, not a quirky
output. The hard part is therefore not "produce an answer"; it is *gating the action*
and recording the decision before it runs.

## The design

No generative model sits in the execution path. A task is evaluated by a deterministic,
rules-based gate — `evaluate_gate()` in `control_plane/governance.py:950` — invoked from
`control_plane/engine.py:808` at the `VALIDATED` workflow state. The gate fails closed:

- Four hard-deny checks return `dead_letter`: unknown role (`governance.py:972-983`),
  unknown classification (`985-994`), classification the role may not read
  (`996-1008`), and an engine the role does not own (`1010-1022`).
- Three boundary checks return `awaiting_approval`: financial cost over the role's
  limit (`1027-1039`), confidence below the autonomy floor of `0.75`
  (`MIN_AUTONOMY_CONFIDENCE`, `governance.py:64`; check at `1042-1054`), and an explicit
  approval request (`1056-1065`).
- Otherwise the task is `EXECUTING` (`1067-1075`).

The load-bearing signal is the **role profile**, not a model score: each role's owned
engines, readable data classifications, and financial limit are structural facts
declared in `organization/role-catalog.yaml` and loaded by
`organization/role_catalog.py`. The WFM demo — the only engine exercised end to end —
takes exactly four numbers, and the bridge injects `is_sample=True` and
`data_mode="simulated_realistic"` server-side (`helix_codex_app/integration/engine_bridge.py:586-587`);
a request carrying `data_classification` or `confidence_score` is refused with `400`
(`helix_codex_app/modules/ops/router.py:223-227`). The decision is written to an
append-only, hash-chained `audit_events` ledger before it runs
(`control_plane/engine.py:839-840`).

## How it was tested

- The local Python 3.12 suite run on 2026-10-31 reported **2,000 passed / 19 deselected**.
  The earlier 2026-09 subset and CI measurements in the original case-study run are
  historical, not current local results.
- The fresh fixture/engine readiness pack passed **12/12 gates**, with 20 calls across
  six engines and two synthetic tenants. The tenant-fidelity checks passed 24/24.
- The App/API tenant and operations drill passed its focused set (**128 tests**) and
  covered persistence, backup/restore, migrations, rollback and cross-tenant controls.
- The simulated design-partner drill passed **14/14 combined checks**. It used the real
  local App HTTP routes, but raw CSV ingestion happened in the readiness harness; the
  App has no CSV upload endpoint. Reviewer checks were deterministic, not independent
  reviews.
- Changed-path Ruff checks passed. Repository-wide Ruff still has 21 existing findings
  and 346 files needing format; do not describe the repository-wide checks as clean.
- Coverage remains at 86.91% only as a historical CI measurement (2026-10-05); it was
  not re-measured in this local run.
- The fail-closed gate has its own tests: `tests/test_governance_fail_closed.py` and
  `tests/test_governance.py` exercise the dead-letter and awaiting-approval branches.
- The WFM demo path is covered by the shared suite (demo bridge at
  `helix_codex_app/integration/engine_bridge.py:529-587`; endpoint at
  `helix_codex_app/modules/ops/router.py:207`).

## What broke

- **CI was red for nine days and hid every later defect.** The workflow failed at step 5
  (`ruff check`) on every push from 2026-09-20 to 2026-09-28 (`AGENTS.md:39-44`, §21).
  Because that step aborted the job, steps 6–17 — the test suite, the security scans, the
  drift checks, both container steps — had **never executed once** in the repo's
  history. The ledger enumerates the root causes (§21.2): an `I001`/`B007` lint error in
  `scripts/generate_pdf.py`, 13 unformatted files, a missing `build`/`hatchling`
  declaration, and — the one to keep in view — nine evidence fixtures signed over CRLF
  bytes (445 B) while the committed blobs are LF (433 B), so they could only ever verify
  on Linux (`AGENTS.md:5104-5117`). I confirmed locally: `ruff check` and
  `ruff format --check` now both exit 0.
- **The pipeline went green for the first time on 2026-09-29** (run `36497766876` on
  `839507e`); fixes were commits `5755667` (clear the ruff failure), `8424b3e` (declare
  the build toolchain, re-sign the nine fixtures over LF), `839507e` (lock-pin count)
  (`AGENTS.md:5121-5137`).
- **During this documentation audit I found the engine scaffolding gap (issue 3 of
  `KNOWN_ISSUES.md`).** Four of six adapters returned synthesized or echoed metrics: B2B
  fabricated `sop_generated=True` (`engines/b2b/adapter.py:326-328`), CRM echoed inputs
  (`engines/crm/adapter.py:311-318`), Personnel hardcoded `pipeline_status` and
  `workforce_headcount` from the request (`engines/personnel/adapter.py:297-322`), and the
  CX scorer used a hardcoded threshold table (`engines/cx/src/risk_scorer.py:57-66`). The
  shared test `tests/test_c4_engines.py:113` passed because it asserts adapters *return
  non-empty metrics*, which the fabrication satisfied. At the time five adapters were
  scaffolding — RTA among them — and the CX AHT unit was incoherent; all have since been
  closed: RTA wired to the engine's `analyze()`, the CX AHT unit resolved, and — in the
  2026-09-30 batch — B2B, CRM and Personnel wired to real engine analytics
  (`fix/b2b-wire-real-onboarding`, `fix/crm-wire-real-pipeline`,
  `fix/personnel-wire-real-pipeline`) and CX's thresholds loaded from
  `config/risk_thresholds.yaml` (`4e4f98d`). All six adapters now drive a real computation
  end-to-end; the audit's scaffolding finding is closed.

## What I decided, and why

- **Fix CI first; do not trust a green badge that has never run the suite.** The
  nine-day red hid pre-existing defects (two undeclared build dependencies, nine CRLF
  fixtures). The suite and the container steps now actually execute. The two container
  steps (16–17) still cannot be reproduced on this machine (Docker is not running here),
  so they rest on the remote green run alone (`AGENTS.md:5152-5153`).
- **Do not claim engine correctness the tests do not show.** Coverage measures code
  execution, not result correctness. I have recorded the former scaffolding gap openly
  rather than letting a passing test count imply that every engine computes correct
  real-world answers.
- **Keep production red by construction.** Nine production-only gates
  (`AGENTS.md:1516-1519`) read external signed evidence and refuse without it. No code
  change can unblock them; they need signatures from keys held outside this repository.

## What is not proven

- No production readiness, customer adoption, or reliability under real customer traffic.
  The six-engine measurements are synthetic-fixture results.
- No real customer traffic or live design-partner run. Scoach Academy Hub remains a
  named opportunity and vertical-pack target, not a participating design partner.
- The engines are exercised on fixtures, but are not independently validated for
  accuracy on real operational data.
- No independent tenant-isolation audit, no external security review, no certified data
  isolation. The 19 cockpit UI tests are quarantined (`AGENTS.md:3454`).
- The WFM implementation now uses the textbook Erlang B recursion and Erlang C
  probability-of-waiting expression, covered by 42 reference tests; fixture results
  still do not establish accuracy on real customer data.
