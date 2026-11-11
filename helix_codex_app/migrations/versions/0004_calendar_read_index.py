"""Index the calendar range read.

Revision ID: 0004_calendar_read_index
Revises: 0003_import_tables
Create Date: 2026-11-11

Why: `list_events` filters `events` by tenant and status and orders by
`starts_at`. EXPLAIN QUERY PLAN on a 2,000-event fixture shows `SCAN events`.
The attendee EXISTS clause is already served by the `event_attendees`
PRIMARY KEY (event_id, account_id) as a COVERING INDEX, so the audit finding
that called for a separate composite index there is corrected: the index
exists, as the primary key. This migration adds the one index that was
genuinely missing.

Additive and reversible: `downgrade` drops only the index it created.
"""
from __future__ import annotations

from alembic import op

revision = "0004_calendar_read_index"
down_revision = "0003_import_tables"
branch_labels = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_events_tenant_status_starts "
        "ON events(tenant_id, status, starts_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_events_tenant_status_starts")
