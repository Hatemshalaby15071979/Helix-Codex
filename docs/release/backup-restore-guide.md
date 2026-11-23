# Helix Prime Codex C8 — Backup, Restore, Rollback Guide

Status: **Production Candidate / Controlled Pilot**

This guide documents the local-first durability procedures for the C8
`backup_restore`, `rollback`, and `audit_integrity` gates. All procedures are
backed by automated verification in `release/backup.py` and its tests.

## What is backed up

- Control-plane store: `control_plane/workflow.db`
- API tenant data (documents, tasks, chat): `control_plane/nodes.db`
- Audit trail: `security/audit.db`
- Integration transport/file state
- Evidence artifacts under `evidence/releases/`

## Backup

The automated backup snapshots the above into a timestamped backup directory and
writes a machine-readable `backup-manifest.json` (transaction-safe SQLite copy).
The Compose profile places the state at the same relative paths beneath `/data`,
so back up that mounted root from the running container:

```bash
docker compose -f infra/docker/docker-compose.yml exec -T helix-api \
  python -c "from release.backup import backup_state; import json; print(json.dumps(backup_state('/tmp/helix-backup', repo_root='/data'), indent=2))"
docker cp "$(docker compose -f infra/docker/docker-compose.yml ps -q helix-api):/tmp/helix-backup" \
  "./helix-backup-$(date -u +%Y%m%dT%H%M%SZ)"
```

## Restore

Restore is always into a **CLEAN, empty** destination directory — never in-place
over live data:

```python
import json
from pathlib import Path
from release.backup import restore_state, schema_compatible, verify_restored_dbs

manifest = json.loads((Path(backup_dir) / "backup-manifest.json").read_text())
compatible, reason = schema_compatible(manifest.get("schema_versions", {}))
if not compatible:
    raise SystemExit(f"restore refused: {reason}")
report = restore_state(backup_dir, target_dir, schema_ok=compatible)
verification = verify_restored_dbs(target_dir, workflow_aggregate="agg-x")
```

`restore_state` rejects a target that is not clean and rejects incompatible
schemas (fail closed). `verify_restored_dbs` proves:
- audit chain integrity preserved across restore,
- workflow events replay in order,
- the API node database passes SQLite integrity checks and contains no blank tenant scope,
- restored state supports safe re-append (idempotency).

Run restore against a copied backup and a new, empty staging directory. Never
remove or overwrite the active data volume until the restored tree has been
verified and an operator has selected a cutover procedure:

```bash
python - <<'PY'
from release.backup import restore_state, verify_restored_dbs
report = restore_state("./helix-backup-<timestamp>", "/tmp/helix-restore-stage")
verification = verify_restored_dbs("/tmp/helix-restore-stage", workflow_aggregate="<workflow-id>")
print(report)
print(verification)
if not verification["verified"]:
    raise SystemExit("restore verification failed; do not cut over")
PY
```

## Rollback

Rolling back to a previous release identity writes the previous manifest's
machine identity and records a rollback marker:

```python
from release.backup import rollback_manifest

rollback_manifest(previous_manifest, active_manifest, target_path=...)
```

## Schema compatibility

`release.backup.schema_compatible` fails closed on unsupported audit/store
schema versions. A restore with an incompatible schema is refused.

## Automated proof

The release gate runs a synthetic backup→restore→verify cycle on isolated temp
state, including a tenant-bearing API node (live DBs are never mutated), and
reports a pass/fail in the `backup_restore` and `rollback` gates. A staging
restore drill does not by itself prove a production volume cutover or disaster
recovery objective; measure and record those separately.
