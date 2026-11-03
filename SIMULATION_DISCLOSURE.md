# Simulation disclosure

**SIMULATION ONLY.** The `simulated_production` profile uses synthetic,
client-shaped fixtures and locally generated machine evidence. A
`SIMULATED_PRODUCTION_READY` result is not a production classification, customer
pilot, independent audit, human approval, legal review, or certification.

The simulation receipt authority is ephemeral and self-contained: its private
key is discarded after signing, while its public key is carried in the evidence
pack. This detects changes to a pack after signing; it does not authenticate an
external authority or independently validate the truth of every producer claim.

No real client data, external service, human/legal approval, or external
certification is implied. Real customer use still requires the separate
activation, security, legal, operational, and deployment evidence recorded in
the release blockers and activation documentation.

Safe claim: “The named local checks passed for the disclosed synthetic
simulation on the recorded source and evidence pack.”
