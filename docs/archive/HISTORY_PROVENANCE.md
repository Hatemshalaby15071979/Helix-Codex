# History & Provenance

This document records how this repository's history should be read. It is a
provenance note, **not** an assurance of independent review.

## Default branch

The default branch is **`release/simulated-production-2026-11`** (a non-standard
name — there is no `main` or `master`). CI and docs-sync target this branch and
run on all branches.

## Commit messages are not evidence

Some commits carry self-asserting messages such as `[gate: … pass]`. These are
**claims by the author**, not proof. The only thing that counts as verification
is a green run of the CI / readiness workflows. Do not treat a commit message as
evidence that a control passed.

## History is not rewritten

Git history in this repository is **not** rewritten. Any change that would alter
existing history requires the owner's explicit **G2** authorization. If you see a
claim that history was "cleaned up," verify it against the actual commit graph
(`git log --all --format='%H %ad %an'`) rather than trusting prose.

## Date provenance (read with care)

It is a known cross-repo pattern in this org that the earliest commit author
dates can precede the GitHub account creation or the repository creation date.
Where that is observed here, it is recorded as a provenance observation, **not**
as evidence of external/independent review, and not as a defect claim. The
simulated-production profile is local, self-verified evidence only.

## What this repo does NOT claim

This repository does not claim: independent or external audit, certification,
legal/privacy review, customer acceptance, or production deployment. Those
remain owner-supplied and, where absent, are recorded as open in the readiness
and status documents.
