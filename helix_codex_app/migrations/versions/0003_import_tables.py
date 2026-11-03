"""Tenant-scoped CSV import tables.

Revision ID: 0003_import_tables
Revises: 0002_route_throttle
Create Date: 2026-11-03

Creates ``import_batches`` (one row per uploaded file, quarantine included) and
``imported_rows`` (the staged rows, one row per source row). Statements are
identical to the ones db.py applies in ``_init_schema`` so a db.py-created
database and an alembic-upgraded database agree; an existing app database
converges on ``alembic upgrade 0003_import_tables``.
"""
from __future__ import annotations

from alembic import op

revision = "0003_import_tables"
down_revision = "0002_route_throttle"
branch_labels = None


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE IF NOT EXISTS import_batches (
        batch_id TEXT PRIMARY KEY,
        tenant_id TEXT NOT NULL,
        client_id TEXT,
        domain_id TEXT,
        filename TEXT NOT NULL,
        table_name TEXT NOT NULL,
        status TEXT NOT NULL,
        rows_total INTEGER NOT NULL DEFAULT 0,
        rows_loaded INTEGER NOT NULL DEFAULT 0,
        rows_rejected INTEGER NOT NULL DEFAULT 0,
        errors_json TEXT NOT NULL DEFAULT '[]',
        provenance_data_mode TEXT NOT NULL DEFAULT 'simulated_realistic',
        created_by TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_import_batches_tenant ON import_batches(tenant_id, created_at DESC)"
    )
    op.execute(
        """
    CREATE TABLE IF NOT EXISTS imported_rows (
        import_id TEXT PRIMARY KEY,
        batch_id TEXT NOT NULL REFERENCES import_batches(batch_id),
        tenant_id TEXT NOT NULL,
        table_name TEXT NOT NULL,
        row_pk TEXT NOT NULL,
        row_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_imported_rows_tenant_table_pk ON imported_rows(tenant_id, table_name, row_pk)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_imported_rows_tenant_batch ON imported_rows(tenant_id, batch_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_imported_rows_tenant_batch")
    op.execute("DROP INDEX IF EXISTS ux_imported_rows_tenant_table_pk")
    op.execute("DROP TABLE IF EXISTS imported_rows")
    op.execute("DROP INDEX IF EXISTS idx_import_batches_tenant")
    op.execute("DROP TABLE IF EXISTS import_batches")
