# Helix Prime Codex C8 — Setup Guide (Reproducible Install)

One-document path to a reproducible local setup for the controlled pilot /
production candidate. Backs the `reproducible_install` and `dependency_locking`
release gates.

## Prerequisites

- Python **3.12** (`python3 --version`) — the repo requires `>=3.12,<3.13`.
- `git`, `pip`.

## One-command setup

From the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
```

The declared development dependency set is mirrored in
`release/requirements.lock.txt`; that lock pins versions but is not a
hash-verified install lock. The API container uses the separately resolved,
hash-verified `release/requirements-api.lock.txt` runtime set, generated from
`release/requirements-api.in` with `scripts/compile_api_lock.sh`. The clean
container install uses pip's `--require-hashes` mode. The API runtime lock does
not include the Streamlit cockpit or test and lint tools.

To regenerate the API lock after changing API dependencies:

```bash
scripts/compile_api_lock.sh
python scripts/check_dependencies.py
```

Review the resulting lock diff, then rebuild and verify the simulated image as
described in `infra/docker/PRODUCTION-SIM-TOPOLOGY.md`.

## Verify

```bash
python3 -m pytest -q          # run the full suite; confirm all results are green
python3 scripts/smoke.py       # engines 6/6, agents 4/4 (registry probes; full 9-agent catalog in organization/role-catalog.yaml)
python3 scripts/health_check.py
python3 scripts/release_gate.py --profile production_candidate
```

## Launch

```bash
helix-api                      # canonical FastAPI spine (loopback 127.0.0.1:8000)
helix-cockpit                  # Streamlit dashboard (secondary)
```

`launch.py --port 8501` remains as a legacy cockpit path.

The API requires one bearer token and one tenant scope per process; it fails
closed when the token is missing. Generate a unique token and export its scope
before launching:

```bash
export HELIX_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export HELIX_API_TOKEN_ROLE=sami
export HELIX_API_TOKEN_TENANT_ID=your-tenant-id
export HELIX_API_TOKEN_CLIENT_ID=your-client-id
helix-api
```

Keep the token in the environment or an approved secret manager, not in source
control, shell transcripts, or logs. For the Docker Compose deployment, the
token and tenant ID are required environment variables; Compose binds its API
and diagnostic cockpit ports to host loopback only. Run a separately scoped
instance with a separate durable data volume for each tenant.

The Compose API image is tagged with `HELIX_API_IMAGE_TAG` (default `local`).
For upgrades, back up first, build with a new unique tag, record its image ID,
and retain the previous tag until rollback is no longer needed:

```bash
export HELIX_API_IMAGE_TAG=20261031T080000Z
docker compose -f infra/docker/docker-compose.yml build
docker compose -f infra/docker/docker-compose.yml up -d --no-build --force-recreate
```

Rollback by selecting the recorded previous tag and recreating with
`--no-build`; never remove the named data volume during a rollback.

## Config validation

Configuration (release profiles + manifest schema) is validated before startup
by the `configuration_validation` release gate.

## Ollama (optional)

Ollama is optional and reported with actionable diagnostics when absent.
Engine adapters run in deterministic sample mode without it.

## Clean-room test isolation

Remove the shared local state before a full-suite run to avoid stale-state
flakes:

```bash
rm -f security/audit.db observability/logs.jsonl control_plane/workflow.db
python3 -m pytest -q
```

These files are gitignored and never committed.
