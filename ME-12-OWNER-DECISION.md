# ME-12 — Owner Decision: Dependabot branches & oversized AGENTS.md — RESOLVED (2026-11-13)

This PR applies the senior-developer recommended options. No destructive remote
actions were taken without review.

## A. Dependabot branches — DECISION: delete stale, do not churn lockfile
The 18 `archive/dependabot/*` (local) and `origin/dependabot/*` (remote) branches
are **stale with 0 open PRs and no cited CVE**. Applying 10 pip bumps blindly to a
126-package, hash-pinned, CI-verified lockfile is a net regression risk.

- **Done in this PR:** removed the local `archive/dependabot/*` branches.
- **Owner follow-up (post-approval):** `git push origin --delete` each
  `origin/dependabot/*` branch to prune remote-tracking noise. Also applies if you
  later want specific version bumps — do them deliberately (edit constraints in
  `requirements*.txt`, `uv pip compile --generate-hashes`, pin CI actions to SHAs).

## B. AGENTS.md (5,776 → 166 lines) — DECISION: split into details
The full historical build ledger is preserved verbatim in **AGENTS.details.md**
(~5,600 lines: all COMPLETE step ledgers §1..§N). **AGENTS.md** is now a concise
orientation (project context, non-negotiable rules, git protocol) + pointer to
AGENTS.details.md. No historical content was lost.

## C. docs/ commercial material (ME-16 flag)
`docs/` still contains commercial/client material (`COMMERCIAL_STORY.md`,
`CASE_STUDY.md`, `HELIX_CODEX_APP_AGENT_PROMPTS.md`). Flagged for the owner to
confirm whether any should move out of the source tree. Left as-is in this PR.

## Status
EXECUTED. Awaiting owner approval/merge of PR #20.
