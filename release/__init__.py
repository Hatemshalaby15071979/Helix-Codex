"""
Helix Prime Codex C8 — release package.

Holds the release profiles/boundary, manifest, backup/restore/rollback,
security gate, observability/readiness, verification harness, and the
release gate orchestrator. This simulation-only branch can produce
SIMULATED_PRODUCTION_READY from verified local receipts, but the production
profile always remains NOT_READY and never emits a production classification.
"""

__version__ = "0.9.0-c8"
