"""BLK-011 regression: a fresh bootstrap must be cockpit-ready.

The cockpit bridge scopes pack data by tenant and client; a bootstrapped
domain without ``client_id`` rendered "no pack data can be scoped" and the
cockpit was unusable on a fresh install. ``bootstrap_owner.py`` now accepts
``--client-id`` (default: the domain name). These tests drive the CLI and
assert the domain row is written with the expected client_id.
"""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "helix_codex_app" / "scripts" / "bootstrap_owner.py"


def _run(
    db_path: Path, *extra: str, password: str = "test-password-123"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--db-path",
            str(db_path),
            "--domain",
            "demo",
            "--username",
            "owner",
            "--password",
            password,
            *extra,
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
    )


def _domain_row(db_path: Path) -> tuple[str, str | None, str | None]:
    conn = sqlite3.connect(str(db_path))
    try:
        return conn.execute(
            "SELECT name, tenant_id, client_id FROM domains WHERE name = 'demo'"
        ).fetchone()
    finally:
        conn.close()


def test_bootstrap_defaults_client_id_to_domain(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    result = _run(db_path)
    assert result.returncode == 0, result.stderr
    assert _domain_row(db_path) == ("demo", "demo", "demo")


def test_bootstrap_explicit_client_id_is_honoured(tmp_path: Path) -> None:
    db_path = tmp_path / "app.db"
    result = _run(db_path, "--client-id", "academy")
    assert result.returncode == 0, result.stderr
    assert _domain_row(db_path) == ("demo", "demo", "academy")


def test_password_via_env_only(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    outcome = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--db-path",
            str(db_path),
            "--domain",
            "demo",
            "--username",
            "owner",
            "--password-env",
            "HELIX_BOOTSTRAP_PASSWORD",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=120,
        env={"HELIX_BOOTSTRAP_PASSWORD": "env-password-123", "PATH": "/usr/bin:/bin"},
    )
    assert outcome.returncode == 0, outcome.stderr
    assert _domain_row(db_path)[0] == "demo"
