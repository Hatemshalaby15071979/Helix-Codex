# 12. Roadmap

Sequenced so each step is gated by evidence. Items below the line are **not yet started** and
depend on the red production gates being satisfied by real evidence.

> **Current state (2026-10-31):** local synthetic tenant/engine and App/API operations
> drills have passed their stated scopes. This does not constitute a real design-partner
> pilot or close any external production gate. The App has no CSV upload/import workflow.

## Near term (within the controlled pilot)
- If an in-App file import is required, design and test a tenant-scoped CSV import path;
  the current drill ingested fixture files through the readiness harness instead.
- Only if a real design-partner engagement is authorized, onboard the participant and
  exit the read-only period under explicit, consented approval (see 10_pilot_plan.md).
- Activate **consented live connectors** for the design partner only, behind the same read-only /
  approval / tenant-isolation controls; keep `live_customer` data mode scoped and audited.
- Add durable memory persistence to the pilot runtime (wire `control_plane.store` or equivalent)
  with backup/restore validated.

## Mid term (broaden capability packs)
- Additional capability packs reusing the core (e.g. field-service, retail).
- Richer restaurant ontology (multi-site, labor law, inventory optimization).
- Human-gated proposal deployment pipeline: approved metacognitive proposals flow to a reviewed
  change with rollback, never automatically.

## Long term (production gating)
- Certified tenant/data isolation audit.
- Independent external observer audit.
- Signed production evidence + security review + legal/privacy review.
- Assigned operational / incident-on-call ownership and disaster-recovery evidence.
- Real, measured cloud cost model (replacing the assumptions in 09).

## Explicitly out of scope (stated, not promised)
- Autonomous operation, universal business coverage, and any "set-and-forget" self-control. The
  system is an accountable, human-approved operating layer by design.
