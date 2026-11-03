# Restore rehearsal checklist (real environment)

Rehearse quarterly and after every upgrade. A rehearsal never touches live
data: verify in place first, then restore into a throwaway directory. Fill
in every evidence field; a rehearsal with blank fields did not happen.

## Run record

- Date:
- Operator:
- Host:
- Backup directory under rehearsal:
- Backup created at (from `backup-manifest.json`):
- Backup bytes:
- Backup duration:
- App image tag and image ID:
- Compose project / volume:

## Verify-only rehearsal

Command:

```
python helix_codex_app/scripts/restore_app.py --backup <backup-dir> --verify-only
```

- Exit code:
- Node count (expected / actual):
- Memory chains verified:
- File inventory problems:
- Audit chain result:
- Release metadata result:
- Restore duration:
- Application health result:
- Last verified backup age (observed RPO at drill):

## Throwaway restore rehearsal

Commands:

```
python helix_codex_app/scripts/restore_app.py --backup <backup-dir> --target <empty-dir>
```

- Exit code:
- Target directory (deleted after the rehearsal):
- Node count (expected / actual):
- Memory chains verified:
- File inventory problems:
- Audit chain result:
- Release metadata result:

## Restart and rollback drill

- Stop/start command and exit codes:
- Synthetic tenant record visible after restart:
- Previous image tag / image ID:
- Image rollback command and health result:
- Original volume retained and verified:

## Migration drill (throwaway copy only)

- App migration drift command and result:
- Control-plane migration drift command and result:
- App database stamp/upgrade command and result:
- Workflow database stamp/upgrade command and result:
- Schema/data verification after migration:
- No live volume targeted (`yes` required):

## Decrypt rehearsal (off-site copies only)

- Decryption command used:
- Decrypted backup verifies clean (`--verify-only` exit code):

## Tamper drill (optional, proves the verification is load-bearing)

- Corruption introduced (e.g. edited one node body in the throwaway copy):
- Restore of the corrupted copy exit code:
- Failing dimension named by the output:

## Sign-off

- Rehearsal result (PASS / FAIL):
- Follow-up actions (if FAIL, link the operator escalation record):
- Operator signature:
- Date:
