"""Driver-level tenant isolation: tenant_id on workflows and events.

Revision ID: 0002_tenant_isolation
Revises: 0001_baseline
Create Date: 2026-11-03

Adds the tenant stamp to every tenant-bearing table that lacked it, backfills
legacy rows from the JSON payload (top-level tenant_id, then
correlation.tenant_id), and adds the supporting indexes. Store applies the same
statements at startup in control_plane/store.py (_migrate_tenant_columns), so a
Store-created database and an alembic-upgraded database agree. Existing
databases stamped at 0001 converge on upgrade head.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "0002_tenant_isolation"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {row[1] for row in bind.execute(text(f"PRAGMA table_info({table})"))}


def upgrade() -> None:
    bind = op.get_bind()
    if "tenant_id" not in _columns(bind, "workflows"):
        op.execute("ALTER TABLE workflows ADD COLUMN tenant_id TEXT NOT NULL DEFAULT ''")
    if "tenant_id" not in _columns(bind, "events"):
        op.execute("ALTER TABLE events ADD COLUMN tenant_id TEXT NOT NULL DEFAULT ''")
    op.execute(
        """UPDATE workflows SET tenant_id = COALESCE(
               json_extract(data, '$.tenant_id'),
               json_extract(data, '$.correlation.tenant_id'),
               '')
           WHERE tenant_id = ''"""
    )
    op.execute(
        """UPDATE events SET tenant_id = COALESCE(
               (SELECT COALESCE(
                   json_extract(w.data, '$.tenant_id'),
                   json_extract(w.data, '$.correlation.tenant_id'),
                   '')
                FROM workflows w
                WHERE w.workflow_id = events.aggregate_id),
               '')
           WHERE tenant_id = ''"""
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflows_tenant ON workflows(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_events_tenant ON events(tenant_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_events_tenant")
    op.execute("DROP INDEX IF EXISTS idx_workflows_tenant")
    op.execute("ALTER TABLE events DROP COLUMN tenant_id")
    op.execute("ALTER TABLE workflows DROP COLUMN tenant_id")
