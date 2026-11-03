# Helix Prime — exploratory conversation draft

> **Not an approved offer or deployment document (status: 2026-10-31).** Helix Prime
> has passed local synthetic-data and tenant/operations drills, but it has no recorded
> real customer pilot or production deployment. The local `PASS_SIMULATED` design-
> partner drill is not customer validation. Do not promise installation, live
> attendance/churn monitoring, pricing, or data import based on this draft.

## What this conversation is for

Learn whether a sports academy has an operational problem that a small, governed
software pilot could address. Statements below are discovery questions, not claims
about any particular academy.

Possible topics:

- How are attendance and schedule changes recorded today?
- Which staff roles need access to which records?
- What data is available, who controls it, and what consent would be required?
- Which single workflow, if any, would be valuable to test first?
- What would the academy require before using any software with its data?

## What exists today

- A sports-academy capability pack exercised with synthetic fixtures.
- Six deterministic engines exercised by a local readiness harness.
- A local App/API workflow with tenant-scoped documents and tasks.
- A local simulated two-tenant drill that passed 14/14 combined checks.

These are engineering test results, not evidence that the software is suitable for a
specific academy, that its outputs are independently validated, or that a customer has
accepted the product.

## Current boundaries

- No real customer deployment, pilot, or customer data is recorded.
- The production profile is `NOT_READY`; nine production-only gates remain open.
- The App has no CSV upload/import endpoint. Do not request or import a real roster
  through the current App.
- No price, free pilot period, contract, or service-level commitment is approved.
- Any future pilot would require separate scope, consent, data-protection review,
  operator ownership, and an explicit go/no-go decision.

## Suggested next step

If there is mutual interest, hold a discovery conversation only. Record confirmed needs
separately from assumptions, and do not imply that a pilot or deployment is available
until the product and required approvals are ready.

See [`PRODUCTION_STATUS.md`](PRODUCTION_STATUS.md) and
[`COMMERCIAL_STORY.md`](COMMERCIAL_STORY.md) for the current project position.
