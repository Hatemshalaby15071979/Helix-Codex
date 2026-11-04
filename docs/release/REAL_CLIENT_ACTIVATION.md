# Real-client activation runbook

**Purpose:** the checklist that turns a verified **simulation** into a real client
deployment. Nothing on this page has been executed with real data.

**SIMULATION ONLY — not authorization.** The current repository state is
`SIMULATED_PRODUCTION_READY` for the `simulated_production` profile with synthetic
fixtures. It is **not** production-ready, has no human/legal/independent approval,
and cannot be deployed to a real client until every step below is completed and
signed by a named human.

Target: one working day of engineering, zero code changes, plus the external time
for legal/security review. Owner roles are placeholders; **no human has been
assigned** and none is claimed.

## Step 0 — Preconditions

| Item | Required state | Evidence | Abort if |
|---|---|---|---|
| Branch | `release/simulated-production-2026-11`, clean tree | `git status` | unexpected changes present |
| Local gate | `SIMULATED_PRODUCTION_READY`, exit 0 | gate log | any red gate |
| Production gate | `NOT_READY`, exit 1 | gate log | it passes before real evidence (treat as defect) |
| Fixtures | client exports received under an agreed DPA | signed DPA | no DPA or unclear lawful basis |

## Step 1 — Receive and classify real exports

- **Owner role:** client data owner + Helix data engineer.
- **Do:** place exports under `HELIX_TENANT_DATA_DIR/<tenant>/`, run the fixture
  validator and classification review; confirm row counts, date coverage, sampling,
  time zones, and restricted fields.
- **Command:** `python scripts/production_readiness/run.py --help`, then the
  documented validation invocation for the tenant.
- **Evidence:** validation report, data-classification memo, row-count reconciliation.
- **Abort if:** any restricted field has no handling decision, or exports are
  incomplete in a way that changes outcomes.

## Step 2 — Run the readiness harness on real exports

- **Owner role:** Helix engineer.
- **Command:**
  `HELIX_TENANT_DATA_DIR=/secure/<tenant> python scripts/production_readiness/run.py`
- **Evidence:** 12/12 gates, engine-call log, run manifest with commit SHA.
- **Abort if:** any gate is red; do not waive a red gate to proceed.

## Step 3 — Import through the App

- **Owner role:** Helix engineer + client admin.
- **Do:** start the App, create the owner, import curated CSVs through
  `/app/import` (preview → commit), tenant-scoped.
- **Evidence:** import IDs, per-table counts, skipped-table list with reasons,
  audit entries.
- **Abort if:** cross-tenant visibility, partial apply, or a hard schema error.

## Step 4 — Re-run isolation and drills on real data

- **Owner role:** Helix engineer.
- **Commands:** cross-tenant attack suite, DR drill ×3, backup/restore rehearsal,
  migration drift checks.
- **Evidence:** zero-leak report, DR report with measured RTO/RPO, drift logs.
- **Abort if:** any leak, failed restore, or audit-chain break.

## Step 5 — Legal / privacy sign-off (human, external)

- **Owner role:** client DPO/legal counsel (named human).
- **Do:** review the DPIA, RoPA, retention schedule, DSR runbook, sub-processor
  list, and DPA. Record lawful basis and any restrictions.
- **Evidence:** signed memo with name, date, scope, and conditions.
- **Abort if:** no named signatory or unresolved DSR/retention gap.

## Step 6 — Security review / penetration test (human, external)

- **Owner role:** client security lead or an independent tester.
- **Do:** review threat model, run or commission a pen-test of the deployed
  topology, review dependency and container findings.
- **Evidence:** signed report, findings with severity, fixes or accepted risks.
- **Abort if:** any unresolved high/critical finding.

## Step 7 — Production evidence and human approval

- **Owner role:** client executive sponsor + Helix release owner.
- **Do:** replace the nine simulated receipts with real evidence, then record a
  genuine `production_approved` sign-off.
- **Command:** `python scripts/record_production_signoff.py` (exact arguments per
  `docs/release/signoff.md`).
- **Evidence:** real evidence bundle + named approval.
- **Abort if:** anyone proposes reusing a simulation receipt as real evidence.

## Step 8 — Flip the profile

- **Owner role:** Helix release owner.
- **Do:** set the profile to `production` in the deployment configuration. The
  fail-closed gate must pass only because the real evidence now exists.
- **Command:** `python scripts/release_gate.py --profile production` (with the real
  evidence directory).
- **Evidence:** `PRODUCTION` classification, exit 0, gate log.
- **Abort if:** the gate needs a code change, a test deletion, or a waiver.

## Step 9 — Deploy the real topology

- **Owner role:** client platform/ops + Helix engineer.
- **Do:** swap the internal CA for the client's CA/DNS, place backups off-host,
  attach monitoring/paging, and deploy using the reviewed topology.
- **Evidence:** deployment record, DNS/TLS proof, monitoring screenshots, backup
  target proof.
- **Abort if:** TLS is the internal CA, backups are host-local only, or paging has
  no named recipient.

## Step 10 — 30-day hypercare

- **Owner role:** named support owner (client + Helix).
- **Do:** daily health review, weekly drift and reconciliation review, incident
  log, and a 30-day retrospective. Any SEV-1 pauses expansion.
- **Evidence:** hypercare log and retrospective.
- **Exit criteria:** zero open SEV-1, drift within agreed bounds, client sign-off.

## What never changes

- A simulation receipt is never presented as external evidence.
- A `SIMULATED_PRODUCTION_READY` result never authorizes a real deployment.
- `PRODUCTION` is emitted only by the fail-closed gate after real evidence and a
  real human approval exist.
