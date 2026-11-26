<div align="center">
  
<img src="https://raw.githubusercontent.com/Hatemshalaby15071979/Helix-Solutions/main/assets/helix-solutions-logo.png" alt="Helix Solutions" width="72" height="72" style="margin-bottom:0.5rem">

# Helix Prime (Helix Codex)

[![CI](https://github.com/Hatemshalaby15071979/Helix-Codex/actions/workflows/ci.yml/badge.svg)](https://github.com/Hatemshalaby15071979/Helix-Codex/actions)
![licence](https://img.shields.io/badge/licence-MIT-blue)
![status](https://img.shields.io/badge/status-v0.9.0%20released-blue)
![Production](https://img.shields.io/badge/production-NOT__READY-red)
![Python](https://img.shields.io/badge/python-3.12%2B-3776ab)

</div>

<p float="left">
  <strong>Helix Prime v0.9.0</strong><br>
  <span style="font-size:0.9em;color:#93aaa0">by Helix Solutions</span>
</p>

The governed, local-first operations core for contact-centre and back-office work —
identity, role-based access, forecasting, CRM, a workflow engine, and a fail-closed
gate, all on your own machine.

## What this is and why it's here

On a live contact-centre floor, the difference between a system people can trust and
one that quietly fails is not cleverness — it is **honesty, boundaries, and a human
who is still in charge**. Automation that decides staffing, churn, or money without a
recorded reason behind it is a breach waiting to happen, not a quirk.

Helix Prime was built to close that gap. It is the one place where identity,
role-based access, the Erlang C forecasting engine, the CRM, the workflow engine, and
a fail-closed gate all live behind a single enforced surface — so a decision is gated,
recorded, and inspectable **before** it runs. No generative model sits in the
execution path: a deterministic gate decides and records every decision, and when
something is missing — a signature, an authority, a confidence level — the system says
*no* instead of guessing.

It is the core of the Helix Codex / Helix Prime body of work. Every other portfolio
repository is a separate codebase by design; satellites talk to it through published,
versioned contracts — never shared source. **Blue Waves** is the one repository that
consumes it as a live external client over those contracts.

## What you get

- **Six engines** — WFM (Erlang C staffing), RTA, CX churn, B2B onboarding, personnel,
  CRM — routed by content across governed role seats.
- **Tenant identity and deny-by-default authorization**, plus a workflow state machine
  with approvals, retries, and dead-letter handling.
- **A fail-closed gate** that checks cost, data classification, confidence, and
  ownership before any execution — and reports a held state instead of forcing a run.
- **An append-only, hash-chained audit ledger** and an exportable governance evidence
  pack, so any decision can be inspected afterwards.
- **Read-only connectors** for Zendesk, Salesforce, and Clay — live writes are
  intentionally disabled.
- **Runs entirely on your machine.** No cloud dependency; Ollama is optional, and
  without it the system runs in deterministic offline mode and says so.

## How to use it

```bash
pip install 'helix-codex-os[web]'     # or: pip install -r requirements.txt
helix-api                             # the governed API spine, binds 127.0.0.1:8000
helix-app                             # the demo app, binds 127.0.0.1:8100
helix-cockpit                         # read-only diagnostic dashboard, 127.0.0.1:8501
```

- **`helix-api`** is where the governance happens — every engine call is gated and
  recorded here first. It refuses to boot in the `production` profile without the
  external gate inputs.
- **`helix-app`** gives you the demo: six engines, nine governed role seats, and the
  gate surface, on synthetic data.
- **`helix-cockpit`** is a read-only dashboard for checking system health without
  touching anything.

The passwordless demo endpoint must never be enabled on a deployed instance.

## The rules we build by

This project obeys `CONSTITUTION.md`: **fail closed** (a missing input or missing
authority is a refusal, never a guess), **evidence before claims** (every published
number carries a command, a date, and an artifact), **local-first and offline by
default**, **a human is always in charge**, and **honest about limits** — simulated
data is labelled simulated, and production gates stay red until real external evidence
is in hand.

## Current status

<!-- docs-sync:start -->
**Released v0.9.0 (local simulation candidate).** This tag marks the published code on the `release/simulated-production-2026-11` branch. 2,107 automated tests pass on local Python 3.12 against synthetic fixtures, and hosted CI now runs on the repository. **This is not production-ready:** it is a simulation classification on synthetic data — no real customer pilot, no independent audit, no certification, no verified revenue — and nine production-only gates remain red by design (signed evidence, certified isolation, external security/privacy review, deployment/DR evidence, named operations/on-call ownership). See [SHIPMENT_READINESS.md](SHIPMENT_READINESS.md) for the full evidence record.
<!-- docs-sync:end -->

## Where things live

- [SHIPMENT_READINESS.md](SHIPMENT_READINESS.md) — the dated evidence record and the
  nine open production gates.
- [docs/PRODUCTION_STATUS.md](docs/PRODUCTION_STATUS.md) — what is claimed and what is
  not, with dates.
- [docs/MASTER_STORY.md](docs/MASTER_STORY.md) — the verified-reality record.
- [docs/](docs/) — architecture, production-readiness, and portfolio references;
  historical plans and superseded constitutions live in [docs/archive/](docs/archive/).
- [tests/](tests/) — the suite CI runs (`pytest -m "not smoke"` with coverage floors).
- [GOVERNANCE.md](GOVERNANCE.md) — the directory map and operating policy.

## Licence & contact

MIT. Built by Hatem Shalaby, Contact Centre Operations & AI Implementation Lead |
WFM & CX Transformation. Background: [github.com/Hatemshalaby15071979](https://github.com/Hatemshalaby15071979) ·
[Hatem Shalaby on LinkedIn](https://www.linkedin.com/in/hatem-shalaby-202902127/)

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
