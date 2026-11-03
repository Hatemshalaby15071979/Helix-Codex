# Synthetic-data privacy boundary check

**SIMULATION ONLY. This is not a legal review or legal advice.**

## Scope exercised

The local readiness harness and App import tests use the documented
CallCenterClient and SportAcademyClient fixtures, whose data classification is
synthetic and whose imported rows carry `simulated_realistic` provenance. The
checks in this branch exercise disclosure, tenant scoping, import validation,
and isolation against those fixtures. No real client, external connector, or
external data processor is involved.

## Machine-checkable boundary

- Fixture classification and disclosure are checked by the readiness harness
  and production-data-boundary tests.
- App import routes derive tenant identity from the authenticated account and
  preserve simulated provenance.
- Cross-tenant reads/writes and malformed fixture imports are covered by
  regression tests.
- `SIMULATION_DISCLOSURE.md` is included with the release evidence.

## Not determined

No lawful basis, jurisdiction-specific retention schedule, DPA, DPIA, real
subject access/deletion/export exercise, breach-notification determination, or
sub-processor approval has been made. Those require an appropriately qualified
human review before real personal data is used. No person has signed or approved
this document; it records only the boundary of the local automated checks.
