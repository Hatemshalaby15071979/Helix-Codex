# Simulated production topology

**SIMULATION ONLY.** This document and `docker-compose.prod-sim.yml` exist to
produce `production_deployment_architecture` evidence for the
`simulated_production` profile. The topology is exercised on one local host. It is
**not** operated by a cloud provider, reviewed by a third party, independently
audited, or approved for real client data. Do not present it as a production
deployment.

## 1. What runs

```
                 host loopback only
 client ──TLS──► 127.0.0.1:8443
                        │
                 ┌──────▼──────┐
                 │    Caddy    │  TLS termination, security headers,
                 │  2.8.4      │  reverse proxy, JSON access log
                 └──────┬──────┘
                        │ compose network :8000
                 ┌──────▼──────┐
                 │  helix-api  │  uvicorn, uid 10001, /readyz probe
                 │             │  /data volume (SQLite + audit ledger)
                 └──────┬──────┘
                        │ fluentd :24224 (async)
                 ┌──────▼──────┐
                 │  log-sink   │  Fluent Bit → helix_sim_logs volume
                 └─────────────┘
```

| Service | Image | Published | Purpose |
|---|---|---|---|
| `caddy` | `caddy:2.8.4` | `127.0.0.1:8443` | TLS, headers, proxy, access log |
| `helix-api` | built from `infra/docker/Dockerfile` | `127.0.0.1:8000` (drill/debug) | API + control plane |
| `log-sink` | `fluent/fluent-bit:3.1.9` | `127.0.0.1:24224` | local JSON log file |

Nothing binds `0.0.0.0` on the host. Caddy reaches the API over the compose
network; the published API port exists only so the drill can call `/readyz`
directly, and can be removed without affecting the TLS path.

## 2. Hardening controls in the compose file

- `read_only: true` on all three services, with explicit `tmpfs` for `/tmp`.
- `cap_drop: [ALL]` on all services; no service needs `NET_BIND_SERVICE` because
  every listener is above port 1024 inside the container. Caddy is the one
  exception: its binary carries file capability `cap_net_bind_service`, and
  executing it with every capability dropped fails with `EPERM`, so that single
  capability is added back while the rest stay dropped.
- `security_opt: [no-new-privileges:true]`.
- Application image already runs as the unprivileged `helix` user (uid 10001).
- TLS via Caddy `tls internal` (local CA). This proves the HTTPS path; it is not a
  publicly trusted certificate. For a real deployment, swap in an operator-managed
  CA/DNS and never present the internal CA as public trust.
- Security headers set at the edge: HSTS, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Permissions-Policy`, and `Server` suppressed.
- Healthchecks are readiness-based: `/readyz` returns 503 while the audit ledger is
  unverifiable, so orchestrators stop routing to a corrupt instance. Caddy waits for
  the API healthcheck before starting.
- Restart policy `unless-stopped` on all services; 30 s stop grace for the API.
- Container logs ship asynchronously to the local sink, so a sink outage does not
  block the API. Logs are JSON lines on the `helix_sim_logs` volume.

## 3. Secrets

Compose `secrets:` mounts four files under `/run/secrets/`. The API command reads
them at process start and exports them into that process only; they never appear in
the compose file, image layers, or `docker inspect` environment.

```sh
infra/docker/prepare-prod-sim-secrets.sh   # writes 0600 files, gitignored
```

`infra/docker/secrets/` is gitignored. Rotate by re-running the script and
restarting the stack. The values are synthetic and authorise nothing outside this
local drill.

## 4. Backup, restore, log rotation, patching

- **Backup:** the API's SQLite databases and memory store live on
  `helix_sim_data`. Use the repository's backup path
  (`helix_codex_app/scripts/backup_app.py`) against a quiesced volume; the DR drill
  in §6 exercises backup → destroy → restore and verifies the audit chain.
- **Restore:** restore into a clean volume, then start the stack and require
  `/readyz` to pass. A failure is a failed drill, not a warning.
- **Log rotation:** the sink writes to a volume; rotate with a host-side logrotate
  or a periodic file mover. Container stdout also remains available under
  `docker compose logs` for short windows.
- **Patching:** the compose file pins exact image tags. Re-pin deliberately,
  rebuild, re-run the drills, and record the new digests. The API image builds
  from `release/requirements.lock.txt`, so dependency changes are reviewable.

## 5. High availability — honest position

**Single host = single point of failure.** There is no active-active, no replicated
database, and no managed load balancer. The HA story is **cold standby**:

1. keep verified backups off the host;
2. provision a standby host with the same compose file and pinned images;
3. restore the latest verified backup;
4. point DNS/tunnel at the standby and require `/readyz`;
5. accept the measured RTO as the recovery budget.

A real client deployment still needs managed DNS/CA, external monitoring, off-host
backup storage, and a tested failover runbook. None of those exist here.

## 6. Validation record (measured 2026-11-04, this host)

| Check | Result |
|---|---|
| `docker compose config` | exit 0 |
| `docker compose up -d --build` | all three containers reached `healthy` |
| HTTPS `/readyz` through Caddy (internal CA, no SNI) | HTTP/2 200; `{"ready":true,...}` |
| Security headers | HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` present; `Server` absent |
| Read-only root / capabilities / user | `ReadonlyRootfs=true`, `CapDrop=[ALL]`, `no-new-privileges`, uid 10001; `CapEff=0`; write to `/` refused |
| Log delivery to `log-sink` | 34 JSON lines from both Caddy and the API in `/logs/prod-sim.log` |
| Teardown | `down -v` removed all four disposable volumes and the network; no containers or volumes remained |
| DR drill ×3 (backup → destroy → restore → verify) | 3/3 PASS; RTO 3.3–3.5 ms, RPO ~0.2 ms, audit chain verified |
| Soak (1,500-seat shape, 2 min at 5 ticks/s) | PASS: 600/600 accepted, 0 errors, p95 2.83 ms, RSS growth ratio 1.001 |

Full capture: `docs/production_readiness/evidence/final-gauntlet-2026-11-04/`
(`https-headers.txt`, `readyz-body.json`, `prod-sim-container-checks.txt`,
`prod-sim-log-sink.log`, `prod-sim-down.log`).

The RTO/RPO above measure the **local restore code path on local disk**, not a
container restart, a cold host, or a provider outage. The 2-minute soak is a
bounded shape check, not the six-hour 1,500-seat soak; the six-hour run is
available via `python scripts/soak_ingest.py --minutes 360 --rate 5` and has not
been executed in this session.

## 7. Break-glass

1. Stop the stack: `docker compose -f infra/docker/docker-compose.prod-sim.yml down`.
2. Start only the API on loopback to inspect `/readyz` and logs.
3. Restore the last verified backup into a **clean** volume; never restore over a
   live volume.
4. Re-run the DR drill and record it before reopening traffic.
5. If the audit chain fails, treat it as SEV-1 and do not serve traffic.

## 8. What this evidence does and does not prove

- Proves: the configuration parses, the containers can start and become ready on
  this host, TLS and headers are applied, logs leave the container, and the local
  restore path recovers verified state.
- Does not prove: provider operation, multi-host failover, capacity under real
  traffic, real-client data handling, independent review, or deployment approval.
