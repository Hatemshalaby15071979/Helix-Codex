# Simulated fixture import

The Helix Codex App can preview and import one curated CSV at a time for the
two synthetic fixture profiles: `callcenterclient` and `sportacademyclient`.
This is simulation-only functionality; it is not evidence that arbitrary or
real client exports have been accepted.

## Route and access contract

Open `/app/import` as an owner or manager. The page carries a persistent
simulation disclosure and offers a preview and a separate import action.
Uploads use the authenticated session and CSRF token:

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/app/import` | Show the tenant's recent batches and upload controls |
| `POST` | `/app/import/preview` | Validate a CSV without writing rows or a batch |
| `POST` | `/app/import/commit` | Import valid rows or persist a quarantine record |
| `GET` | `/app/import/{batch_id}` | Read a batch only within the authenticated tenant |
| `POST` | `/app/import/{batch_id}/discard` | Remove that tenant's imported rows and record an audit node |

Unknown permissions, missing sessions, missing CSRF tokens, and cross-tenant
batch IDs fail closed. Tenant and client identifiers come from the authenticated
account, never from form fields.

## Validation and persistence

- UTF-8 CSV only; strict CSV parsing; duplicate headers, unknown shapes, wrong
  tenant profile, bad row widths, duplicate/empty primary keys, and invalid
  numeric/date/boolean values are rejected.
- The header must exactly match a schema in
  `helix_codex_app/modules/imports/schema.py`. Only the two named fixture
  client IDs are accepted.
- A file is capped at 25 MiB and 100,000 rows. The upload is not stored as a
  raw file; normalized row JSON is stored in `imported_rows`.
- Commit is one transaction. Validation failures produce a tenant-stamped
  `quarantined` batch and audit node, and no data rows. A failed transaction
  rolls back both rows and batch.
- Re-import is idempotent on `(tenant_id, table_name, row_pk)`; a successful
  re-import updates the staged row and associates it with the newest batch.
- Every batch and audit node carries `simulated_realistic` provenance. The
  import API rejects an empty tenant scope with `TenantScopeMissing`.

The regression suites
`tests/helix_codex_app/test_imports_service.py` and
`tests/helix_codex_app/test_imports_routes.py` cover tenant-profile mismatch,
quarantine, idempotency, provenance, permission/CSRF checks, and cross-tenant
batch visibility. They use synthetic test rows, not a real client connection.
