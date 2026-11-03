# ADR-0002: Simulation-only release profile

**Status:** Accepted for the `release/simulated-production-2026-11` branch  
**Date:** 2026-11-03

## Context

Nine release gates require external authority, an independent party, or real
operational evidence. This execution is restricted to local synthetic fixtures
and cannot obtain those things. Calling the gates green without a visible,
verifiable substitution would misrepresent the evidence.

## Decision

Add a `simulated_production` profile requiring all 14 core gates and all nine
otherwise-external gates. The nine substitutions require explicit simulation
disclosure, evidence JSON, a SHA-256 profile-bundle digest, ML-DSA-65 signatures,
and an ordered hash-chained receipt for each gate. Verification checks the
bundle digest, manifest signature, evidence hashes, receipt signatures, receipt
order, and chain links. The external-observer substitution also runs the
verifier in a separate local process.

The simulation authority key is generated in a temporary directory for each
pack. The private key is not retained. The public key is stored with the pack,
so this mechanism demonstrates integrity and tamper detection after creation;
it does **not** establish an independently trusted identity or prove that the
evidence producer was honest.

The `production` profile always returns `NOT_READY` on this branch. Manifest
generation rejects a bare `PRODUCTION` classification. The simulated profile
does not consult or claim human approval: its manifest records
`release_approved: false`. A successful result is named
`SIMULATED_PRODUCTION_READY` and is limited to the evidence actually exercised.

## Consequences and limits

- Local signatures are machine-generated integrity checks, not external
  signatures, human approvals, independent certification, or legal advice.
- A second local process is not an independent organization or reviewer.
- Evidence is only as trustworthy as its measured inputs; a signed statement
  does not make an unrun test true.
- Synthetic tenant fixtures do not establish customer-data, jurisdictional,
  production-scale, cloud, or on-call readiness.
- The production-only gate implementations remain fail-closed outside the
  simulated profile.

## Verification

`tests/test_simulation_release_evidence.py` exercises signature creation,
private-key absence, wrong-bundle rejection, receipt/evidence tamper rejection,
missing evidence rejection, and release-gate binding. Migration and driver
isolation checks remain covered by their existing dedicated suites.
