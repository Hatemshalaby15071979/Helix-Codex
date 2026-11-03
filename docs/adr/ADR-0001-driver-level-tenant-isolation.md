# ADR-0001 — Driver-level tenant isolation (2026-11-03)

**Status:** Accepted (2026-11-03)
**Scope:** `control_plane/store.py` (workflow DB), `server/models/store.py` (nodes DB), `migrations/versions/0002_tenant_isolation.py`
**Blockers closed:** BLK-008 (driver-level isolation)

## Context

Tenant isolation was enforced at the policy seam (`security/policy.py::authorize`) before any
request reached storage, and at tested HTTP routes in the App/API drill. It was **not** enforced
inside the stores: a bug that reached SQL with a foreign tenant's id would read or overwrite that
tenant's rows. Two concrete weaknesses were identified and fixed:

1. `NodeStore.create` used `INSERT OR REPLACE` — a caller supplying another tenant's `node_id`
   would silently overwrite the stored row (tenant stamp included — the attacker's envelope won).
2. `workflows`/`events` carried no tenant column at all, so no SQL-level predicate existed.

## Decision

1. Every tenant-bearing table carries `tenant_id` on the row itself:
   - `workflows`, `events` gain `tenant_id` (idempotent `ALTER TABLE` at `Store` open and in
     migration `0002_tenant_isolation`; legacy rows backfilled from JSON
     `$.tenant_id` → `$.correlation.tenant_id`).
   - `workflow_tasks` already carried `tenant_id`.
   - `audit_events` deliberately carries **no** tenant column (the ledger is shared and its hash
     chain must remain uniform). Scoped reads are enforced with an `EXISTS` subquery against
     `workflow_tasks`; rows that cannot be tied to the tenant are invisible.
2. Scoped reads are SQL-level, never post-filtered in Python:
   `get_workflow_scoped`, `get_events_scoped`, `list_workflows(tenant_id=…)`,
   `get_workflow_task(task_id, tenant_id=…)`, `list_workflow_tasks(tenant_id=…)`,
   `list_audit_events(tenant_id=…)`.
3. An empty-string tenant is refused everywhere (`TenantScopeMissing`) — fail closed.
4. `NodeStore.create` uses plain `INSERT`; a `node_id` collision raises `NodeExistsError` and
   leaves the stored row untouched.
5. The engine's single-process internals (`get_workflow`, `get_events`, `replay`, audit hash
   chain verification) remain unscoped **by design**: they run after the authorization gate,
   never on a cross-tenant HTTP path, and external callers have no route to them. App-facing
   reads take the scoped variants.

## Consequences

- Cross-tenant reads through the stores return nothing (tested: `tests/test_tenant_isolation_driver.py`).
- Cross-tenant overwrite of a node is impossible (tested).
- Migration is backward compatible: existing databases stamp at `0001_baseline`, converge at
  `alembic upgrade head` (0002), and Store-created databases agree — `scripts/check_migration_drift.py`
  reports 21/21 objects (19 + 2 indexes).
- Cost: one extra `SELECT` in `append_event` (tenant lookup) — negligible; one-off backfill
  UPDATE guarded by `WHERE tenant_id = ''`.
- **Not claimed:** independent certification; real-client data; driver-level proof for tables
  created by the App's own DB (covered by App-layer drills instead). This closes the
  *independent certification* portion of the gate only when paired with the simulated observer
  audit (P5) — and never upgrades a `simulated` label into a human claim.
