# Helix Prime tenant isolation and operations drill

**Run date:** 2026-10-31 UTC  
**Scope:** local Docker deployments with synthetic tenants and disposable volumes  
**Result:** App/API drills passed; this is not production authorization.

No customer data, production secrets, external deployment, or push was used.
The C8 production-only external signatures remain outstanding, so Helix Prime
is still **NOT_READY_FOR_FIRST_CUSTOMER_DEPLOYMENT**.

## Tenant isolation and persistent data

- The API profile ran with a dummy, tenant-scoped token for
  `tenant-ops-drill`. `/readyz` returned ready; scoped document create/read
  worked, a tenant override was denied with HTTP 403, and the synthetic row
  survived container restart. The API backup included `nodes.db`; restore
  verification passed and a checksum-tampered copy was rejected.
- The App profile exercised two synthetic tenants, `drill-tenant-a` and
  `drill-tenant-b`, through the running HTTP app: both logins returned 303,
  both document creates returned 201, a CSRF-less write returned 403, a
  foreign document read returned 404, and tenant lists returned 200 without
  cross-tenant document visibility. Restart preserved both tenants' records.
- The final App image returned HTTP 200 from `/app/healthz`; its two tenant
  node counts were 3 and 3. Restart-to-HTTP-ready measured **2.88 seconds**.
  The API `/readyz` returned `{"ready":true,"checks":{"workflow_store":true,"audit_chain":true},"detail":null}`.
- Focused regression tests for API/App tenant scope, HTTP auth, backup/restore,
  Compose security, and migration drift: **128 passed**.

## Backup, restore, migrations, and rollback

- App image: `helix-prime-codex-app:drill-20261031t0630z`,
  image ID
  `sha256:0c38cb61957b3e4675b4be002d33fab37d2eb0c79902130ba863dacc6b24fda3`.
- App backup manifest SHA-256:
  `abe2c17e7e171f62ffaa90dee2a5a7fc0c2a283f3f6afb129470ce49201cd78f`.
  The manifest recorded 6 app nodes, three captured SQLite files, and a valid
  empty audit chain.
- `restore_app.py --verify-only` passed in the container with the backup
  mounted `:ro`. Verification hashes the original snapshot, checks databases
  in a temporary writable copy, and leaves the source backup unchanged.
- Restore to the isolated project volume passed:
  `restored /data (nodes=6 chains_verified=True)`. App schema drift was
  63/63 objects; control-plane drift was 19/19. Both restored databases
  passed Alembic `stamp head` and `upgrade head`. The restored app became
  healthy and retained three nodes for each tenant.
- Rollback to `helix-prime-codex-app:rollback-baseline`
  (`sha256:a4bdc8d4ae7d08be4d51bc94abfd366a1cf4e3a496c13484af332a32edc0b146`)
  against the retained original volume returned HTTP 200 and retained both
  tenant records. The candidate image was then restored against that volume
  and also returned HTTP 200.

The verifier regression is covered by
`tests/helix_codex_app/test_backup_procedure.py`: verify-only succeeds and
does not change backup file hashes; tampering still fails verification.

## Verification commands

Run from the Helix-Prime repository root; the workspace Python 3.12
environment is used for project checks.

```bash
../../.venvs/helix-prime/bin/python -m pytest \
  tests/test_api_tenant_scope.py tests/test_c8_release_gate.py \
  tests/test_docker_compose_security.py tests/test_migration_drift.py \
  tests/helix_codex_app/test_auth_hardening.py \
  tests/helix_codex_app/test_login_and_auth.py \
  tests/helix_codex_app/test_docs_isolation.py \
  tests/helix_codex_app/test_tenant_isolation.py \
  tests/helix_codex_app/test_backup_procedure.py \
  tests/helix_codex_app/test_app_migration_drift.py -q

../../.venvs/helix-prime/bin/ruff check \
  helix_codex_app/scripts/restore_app.py \
  tests/helix_codex_app/test_backup_procedure.py
../../.venvs/helix-prime/bin/ruff format --check \
  helix_codex_app/scripts/restore_app.py \
  tests/helix_codex_app/test_backup_procedure.py
../../.venvs/helix-prime/bin/python helix_codex_app/scripts/check_app_migration_drift.py
../../.venvs/helix-prime/bin/python scripts/check_migration_drift.py
```

The focused test command completed with 128 passed; Ruff check and format
reported clean; both migration drift commands reported no drift.

## Cleanup and disposition

The original App, restored App, and API Compose projects and their synthetic
named volumes were stopped and removed after evidence capture. The named
`/tmp/helix-*` backup, tamper, restore-stage, and baseline-build directories
were also removed. Local image tags were retained for reproducibility.
Changes remain uncommitted and were not pushed.
