#!/usr/bin/env sh
# SIMULATION ONLY — create disposable credentials for the prod-sim topology.
#
# Writes four single-line secret files under infra/docker/secrets/ (gitignored).
# Re-running rotates them; restart the stack afterwards. The values are synthetic:
# they authorise nothing outside this local drill.
#
# Mode is 0644 (not 0600) on purpose: Docker Compose (non-swarm) mounts `file:`
# secrets preserving the host file's mode/ownership and ignores per-secret
# uid/gid/mode overrides (those are Swarm-only). The helix-api container runs as
# the non-root user `helix` (uid 10001), so a 0600 file is unreadable and the
# service fails to start. 0644 lets the non-root container user read the
# synthetic secret. These are random drill secrets, not real credentials.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
secrets="$here/secrets"

umask 077
mkdir -p "$secrets"

python3 - "$secrets" <<'PY'
import secrets
import sys
from pathlib import Path

target = Path(sys.argv[1])
values = {
    "helix_api_token": secrets.token_urlsafe(48),
    "helix_api_token_role": "sami",
    "helix_api_token_tenant_id": "prod-sim-tenant",
    "helix_api_token_client_id": "prod-sim-client",
}
for name, value in values.items():
    path = target / name
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(0o644)
    print(f"wrote {path}")
PY

echo "prod-sim secrets ready under $secrets (mode 0600, gitignored)"
