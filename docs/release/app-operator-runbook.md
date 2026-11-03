# Helix Codex App — Operator Runbook

Operational procedures for running the Helix Codex App in a self-hosted
environment. This runbook covers health checks, logs, backup and restore,
and common troubleshooting steps.

## Architecture

The app runs as a single Docker container. Its persistent volume holds the
app SQLite database and governed memory tree, plus the workflow and audit
databases used by the app process. It serves the web UI on
http://127.0.0.1:8100. There are no external dependencies — no Redis, no
message broker, no separate database server.

Data lives in a Docker named volume (`helix_app_data`) mounted at `/data`.
This volume is independent of the API profile's `helix_data` volume; the
two Compose profiles are separate deployments and do not share database
state. Back up each deployment through its own procedure.
Inside the image `/data` is owned by the unprivileged `helix` user
(uid 10001) and is the only writable application path; the app itself runs
as that user, never as root. On the host, the volume contents are managed
by Docker — never `chmod` or `chown` the volume files directly while the
container is running.

## Health check

The container runs a built-in health check every 30 seconds. Check status:

```
docker compose -f infra/docker/docker-compose.app.yml ps
```

A healthy app shows "healthy" under STATUS. The health check verifies that
the web server responds on `http://127.0.0.1:8100/app/healthz`.

Manual check:

```
curl -s http://127.0.0.1:8100/app/healthz
```

Returns HTTP 200 with `{"status":"ok","app":"helix-codex"}` when the app is
running.

`healthy` means the app endpoint responds. The separate API Compose profile
has `/readyz` for API readiness; it is not an app health endpoint. Consult
the `infra/monitoring/README.md` alert catalog and release gates for the
readiness story.
After any upgrade or restore, check `healthy` here, then work through the
restore-rehearsal checklist before letting users back in.

## Logs

View the app logs:

```
docker compose -f infra/docker/docker-compose.app.yml logs helix-app
```

Follow logs in real time:

```
docker compose -f infra/docker/docker-compose.app.yml logs -f helix-app
```

The app writes structured log lines to stdout (one per request, with
correlation id, route, status code, and duration). Error messages appear
in the same stream.

## Backup

The backup copies the app database and the memory store tree into a
backup directory with a manifest:

```
docker compose -f infra/docker/docker-compose.app.yml exec helix-app \
    python helix_codex_app/scripts/backup_app.py \
    --db-path /data/helix_codex_app/app.db \
    --memory-root /data/helix_codex_app/memory_stores \
    --audit-db-path /data/security/audit.db \
    --workflow-db-path /data/control_plane/workflow.db \
    --target /tmp/backup
```

Copy the backup out of the container:

```
docker cp \
    $(docker compose -f infra/docker/docker-compose.app.yml ps -q helix-app):/tmp/backup \
    ./helix-backup-$(date +%Y%m%d)
```

The backup includes this deployment's app database, governed memory tree,
workflow database, and audit database; release metadata is optional when a
generated manifest is available. Its manifest records each captured file's
SHA-256, app node count, audit-chain status, and memory-chain verification.
Missing requested databases, invalid audit chains, and invalid memory chains
cause a non-zero result. The API profile uses a
separate Docker volume and its own backup procedure in
`docs/release/backup-restore-guide.md`; this app backup does not cover API
documents, tasks, or chats.

**Schedule:** Run a backup daily if the app is in active use.

## Scheduled backups

Run the backup command inside the healthy container and copy the result to
durable host storage immediately. Name every backup directory with a
timestamp (`helix-backup-YYYYMMDD-HHMMSS`). The example captures all app
state databases and memory stores. Pass `--release-manifest` if the deployed
release provides a generated manifest file.

Linux (cron, daily at 02:00):

```
0 2 * * * mkdir -p /srv/backups && STAMP=$(date +\%Y\%m\%d-\%H\%M\%S) && docker compose -f /opt/helix/infra/docker/docker-compose.app.yml exec -T helix-app python helix_codex_app/scripts/backup_app.py --db-path /data/helix_codex_app/app.db --memory-root /data/helix_codex_app/memory_stores --audit-db-path /data/security/audit.db --workflow-db-path /data/control_plane/workflow.db --target /tmp/helix-backup-$STAMP && docker cp $(docker compose -f /opt/helix/infra/docker/docker-compose.app.yml ps -q helix-app):/tmp/helix-backup-$STAMP /srv/backups/helix-backup-$STAMP && python /opt/helix/helix_codex_app/scripts/backup_app.py --prune-root /srv/backups --keep-last 7 --keep-days 30
```

macOS: the same commands under `launchd` (a `StartCalendarInterval` plist
calling the script above). Windows: Task Scheduler running
`docker compose ... exec` plus the prune command with the same flags.

## Retention policy

Keep the last **7** daily backups and everything from the last **30** days
(`--keep-last 7 --keep-days 30`, the prune defaults). Pruning only ever
deletes directories that carry their own `backup-manifest.json`, never
deletes the newest backup, and leaves a root with fewer than two backups
alone — run it with `--dry-run` first after any change. Retention runs
after the backup in the same scheduled job, so a failed backup never
deletes its predecessors.

## Encrypted destinations

The app performs no application-level cryptography on backups, by design.
Protect them with the platform instead: BitLocker (Windows), FileVault
(macOS), or LUKS (Linux) on the volume that holds `/srv/backups`, or wrap
each backup directory for off-site copies with a file-level tool you
already trust:

```
age -r <recipient> -o helix-backup-20260918-020000.tar.age <backup-dir>
```

Store the decryption key offline, separate from the backups. A backup you
cannot decrypt is not a backup — rehearsal (below) must include a decrypt.

## RPO / RTO

The daily schedule is a proposed 24-hour backup interval, not a measured
recovery-point guarantee. Record the age of the last verified backup at
incident time to calculate observed RPO. Do not claim an RTO until a timed
restore rehearsal includes verification and a successful application health
check; record elapsed time and data volume in the rehearsal checklist.

## Backup failure alert and escalation

`backup_app.py` exits non-zero on missing state, write errors, or invalid
integrity checks (write errors print `app backup failed: <reason>`). Wire the scheduler to alert
on a non-zero exit (cron mail, Task Scheduler event, or your monitor
watching the job log). On a backup failure:

1. Do **not** upgrade, restart, or prune. The previous backups are still
   valid — a failed backup must never delete its predecessors.
2. Check disk space on the backup destination and the `/data` volume.
3. Re-run the backup by hand. If it still fails, escalate to the operator
   with the exact stderr line, the backup directory name, and the last
   known-good backup (name + date).

## Restore

Do not delete the active volume to make room for a restore. Keep it as the
rollback copy and restore into a new Compose project (which gets a separate,
empty named volume):

```
docker compose -f infra/docker/docker-compose.app.yml down
```

First verify the backup and restore it into the new project's `/data` volume.
Verification hashes the mounted snapshot and checks its databases in a
temporary writable copy, so the original backup can remain read-only and
unchanged.
Replace the project name with a new, unused lowercase identifier:

```
RESTORE_PROJECT=helix-restore-$(date -u +%Y%m%d%H%M%S)
BACKUP_DIR=/srv/backups/helix-backup-YYYYMMDD-HHMMSS
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml \
    run --rm -v "$BACKUP_DIR:/backup:ro" helix-app \
    python helix_codex_app/scripts/restore_app.py --backup /backup --verify-only
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml \
    run --rm -v "$BACKUP_DIR:/backup:ro" helix-app \
    python helix_codex_app/scripts/restore_app.py --backup /backup --target /data
```

Start the restored project and confirm health and representative tenant
workflows before directing users to it:

```
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml up -d
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml ps
```

The original project's volume is intentionally retained until the restored
deployment is accepted. If the restored instance fails, stop it and start the
original project again:

```
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml down
docker compose -f infra/docker/docker-compose.app.yml up -d
```

Never use `down -v` or remove either volume as part of the restore procedure.

Restore success requires verification, never merely file copying. After
the copy, `restore_app.py` proves five things and refuses the restore
(exit 1) if any of them fails:

1. The app database holds exactly the manifest's node count.
2. Every governed memory chain verifies.
3. Every captured file matches the manifest's sha256 inventory
   (a tampered backup fails here even when the counts still match).
4. The captured audit database chain verifies (when captured).
5. The captured release manifest matches its recorded hash (when captured).

The restore also refuses before copying when the backup version is
unsupported or the target directory is not empty — restoring into a
non-empty target is never allowed, because it could mix live data with
backup data.

Rehearse a restore without touching live data first:

```
python helix_codex_app/scripts/restore_app.py --backup <backup-dir> --verify-only
```

Exit 0 means the backup would restore clean; exit 1 names the failing
dimension. Rehearse quarterly and after every upgrade, and record the run
in `docs/release/restore-rehearsal-checklist.md` — the checklist ships
with empty evidence fields for the operator to fill in.

After a successful restore, the new project runs from the restored volume. The
restore script verifies the staged copy; the operator must still exercise the
live deployment before declaring recovery complete.

## Schema and migration drill

Run both drift checks against the release image before an upgrade. They build
temporary databases and compare application-created schemas with the migration
heads; they do not target the mounted data volume:

```
docker compose -f infra/docker/docker-compose.app.yml exec -T helix-app \
    python helix_codex_app/scripts/check_app_migration_drift.py
docker compose -f infra/docker/docker-compose.app.yml exec -T helix-app \
    python scripts/check_migration_drift.py
```

For an existing database, rehearse Alembic only against the restored throwaway
volume. First confirm schema drift checks pass, then stamp the schema already
created by the app and apply the head:

```
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml \
    exec -T helix-app python -m alembic -c helix_codex_app/alembic.ini \
    -x db=/data/helix_codex_app/app.db stamp head
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml \
    exec -T helix-app python -m alembic -c helix_codex_app/alembic.ini \
    -x db=/data/helix_codex_app/app.db upgrade head
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml \
    exec -T helix-app python -m alembic -c alembic.ini \
    -x db=/data/control_plane/workflow.db stamp head
docker compose -p "$RESTORE_PROJECT" -f infra/docker/docker-compose.app.yml \
    exec -T helix-app python -m alembic -c alembic.ini \
    -x db=/data/control_plane/workflow.db upgrade head
```

Verify the restored tenant rows and health endpoint after the drill. Never
stamp, upgrade, or otherwise rehearse migrations against the active volume.

## Upgrade safely (backup first)

Never upgrade without a fresh, verified backup. Compose keeps versioned
image tags when a unique `HELIX_APP_IMAGE_TAG` is supplied; record the
currently deployed tag before choosing a new one. Do not reuse or delete the
previous tag until the upgrade is accepted.

1. Back up and verify first (see **Backup** above). Copy the backup folder
   out of the container.
2. Record the current image tag and select a new, unique tag:
   ```
   docker compose -f infra/docker/docker-compose.app.yml images
   export HELIX_APP_IMAGE_TAG=20261031T080000Z
   docker compose -f infra/docker/docker-compose.app.yml build --pull
   ```
   The build installs dependencies from the pinned
   `release/requirements.lock.txt`. Each tag remains available locally for
   rollback; also record its image ID with `docker image inspect`.
3. Recreate the container without removing the volume:
   ```
   docker compose -f infra/docker/docker-compose.app.yml up -d --no-build --force-recreate
   ```
   (`down` without `-v` also preserves the volume. Never use `down -v`
   for an upgrade — that deletes all data.)
4. Verify: wait for `healthy` in `ps`, then open the app and log in.
5. To roll back the image while retaining the same data volume, select the
   recorded previous tag and recreate without building:
   ```
   export HELIX_APP_IMAGE_TAG=<previous-tag>
   docker compose -f infra/docker/docker-compose.app.yml up -d --no-build --force-recreate
   docker compose -f infra/docker/docker-compose.app.yml ps
   ```
   If the database itself must be reverted, stop this project and restore
   into a separate project as described in **Restore**; never overwrite or
   remove the last-known-good volume during an incident.

## Evidence export

Owners can export a full evidence dossier from the Admin screen
(**Admin > Evidence export**). The download is a zip containing the
audit trail, node counts, memory chain verification, and the release
manifest.

## Remote access, TLS, and cookies

The app binds to loopback only and refuses to start on any other address.
For access beyond the host, terminate TLS at a reverse proxy on the same
machine (nginx, Caddy, or an SSH tunnel/VPN) and forward plain HTTP to
`http://127.0.0.1:8100`. Never expose the app socket directly.

Cookie and TLS requirements:

- `HELIX_APP_COOKIE_SECURE` stays `true` (the default) whenever browsers
  reach the app over HTTPS. Every session cookie is `HttpOnly`, `SameSite=Lax`,
  `Path=/`, and `Secure` under that setting. Behind plain HTTP the `Secure`
  cookie is never sent, so local plain-HTTP development is the only
  configuration that sets it to `false` — and disabling it through the
  environment refuses to start unless `HELIX_APP_ALLOW_INSECURE_COOKIES=true`
  is set alongside, so a production container can never drift insecure
  silently.
- The app does not interpret `X-Forwarded-For` or `X-Forwarded-Proto`: the
  address recorded in `login_events` and used for login throttling is the
  immediate peer, so run exactly one proxy on the same host.
- Session lifetime follows `HELIX_APP_SESSION_IDLE_MINUTES` (idle expiry)
  and `HELIX_APP_SESSION_ABSOLUTE_DAYS` (hard ceiling); a password change
  revokes every session for the account immediately.
- Sign-in is throttled per source address and per login name in fixed
  windows (SQLite-backed, bounded); repeated failures also lock the account
  for 15 minutes. All credential failures share one message, so throttling
  and lockout never reveal whether a domain, username, or password was wrong.

## Troubleshooting

### App won't start ( unhealthy after 2 minutes )

1. Check logs: `docker compose -f infra/docker/docker-compose.app.yml logs helix-app`
2. Common causes:
   - The database file is locked by another process
   - The `/data` volume is full
   - A previous shutdown left a WAL file

### Bootstrap script says "domain already exists"

The domain was already created. You can log in with any existing owner
account, or create a new owner through the Admin screen.

### Cannot reach http://127.0.0.1:8100 from another machine

This is by design. The app binds to your machine's loopback address
and cannot accept connections from other machines. Use an SSH tunnel
or VPN for remote access.

### Password forgot / locked out

If you have access to the database file, the operator can reset the
password by running the bootstrap script with a new password and a
different domain, then creating a new owner. Alternatively, restore a known-good backup into a new volume as described
above. Do not remove the active database or memory tree as a password-reset
shortcut; that destroys tenant data.

### Container won't stop

Use `docker compose ... stop` or `down` to stop the service. Both preserve its
volume. Volume removal is a separate, destructive maintenance action and is
not part of incident recovery.
