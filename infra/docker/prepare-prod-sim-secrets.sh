#!/usr/bin/env sh
# SIMULATION ONLY — create disposable credentials for the prod-sim topology.
#
# Writes four single-line secret files under infra/docker/secrets/ (gitignored),
# mode 0600. Re-running rotates them; restart the stack afterwards. The values
# are synthetic: they authorise nothing outside this local drill.
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
    path.chmod(0o600)
    print(f"wrote {path}")
PY

echo "prod-sim secrets ready under $secrets (mode 0600, gitignored)"
