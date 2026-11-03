from __future__ import annotations

import csv
import io
from types import SimpleNamespace

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
TestClient = fastapi_testclient.TestClient

from helix_codex_app import db
from helix_codex_app.app import create_app
from helix_codex_app.config import AppSettings
from helix_codex_app.modules.imports.schema import SCHEMAS
from helix_codex_app.security.accounts import AccountRepository
from helix_codex_app.security.passwords import hash_password
from helix_codex_app.security.sessions import SESSION_COOKIE, SessionStore


@pytest.fixture()
def app_context(tmp_path, monkeypatch):
    db_path = str(tmp_path / "app.db")
    conn = db.connect(db_path=db_path)
    db._init_schema(conn)
    repo = AccountRepository(conn)
    callcenter_domain = repo.create_domain(
        "callcenter.test",
        tenant_id="tenant-cc",
        client_id="callcenterclient",
    )
    academy_domain = repo.create_domain(
        "academy.test",
        tenant_id="tenant-sa",
        client_id="sportacademyclient",
    )
    owner = repo.create_account(
        callcenter_domain.domain_id,
        "owner",
        role_id="owner",
        password_hash=hash_password("test-password"),
    )
    employee = repo.create_account(
        callcenter_domain.domain_id,
        "employee",
        role_id="employee",
        password_hash=hash_password("test-password"),
    )
    other_owner = repo.create_account(
        academy_domain.domain_id,
        "owner",
        role_id="owner",
        password_hash=hash_password("test-password"),
    )
    settings = AppSettings(db_path=db_path, cookie_secure=False)
    sessions = SessionStore(conn, settings)
    monkeypatch.setenv("HELIX_DB_PATH", str(tmp_path / "workflow.db"))
    monkeypatch.setenv("HELIX_AUDIT_DB_PATH", str(tmp_path / "audit.db"))
    monkeypatch.setenv("HELIX_LOG_PATH", str(tmp_path / "logs.jsonl"))
    from server.config import get_settings

    get_settings.cache_clear()
    with TestClient(create_app(settings), follow_redirects=False) as client:
        yield SimpleNamespace(
            client=client,
            conn=conn,
            sessions=sessions,
            owner=owner,
            employee=employee,
            other_owner=other_owner,
        )
    get_settings.cache_clear()
    db.close(conn)


def _session(ctx, account):
    token, session = ctx.sessions.issue_session(account)
    return {SESSION_COOKIE: token}, {"X-CSRF-Token": session.csrf_token}


def _fixture_csv(table_name: str, primary_key: str = "fixture-row") -> bytes:
    table = next(item for item in SCHEMAS if item.table_name == table_name)
    row = {table.primary_key[0]: primary_key}
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(table.columns)
    writer.writerow([row.get(column, "") for column in table.columns])
    return output.getvalue().encode()


def test_import_page_discloses_simulation_and_owner_can_open(app_context):
    cookies, _ = _session(app_context, app_context.owner)
    response = app_context.client.get("/app/import", cookies=cookies)

    assert response.status_code == 200
    assert "SIMULATION" in response.text
    assert "simulated_realistic" in response.text


def test_import_permission_and_csrf_are_enforced(app_context):
    employee_cookies, _ = _session(app_context, app_context.employee)
    denied = app_context.client.get("/app/import", cookies=employee_cookies)
    assert denied.status_code == 403

    owner_cookies, _ = _session(app_context, app_context.owner)
    no_csrf = app_context.client.post(
        "/app/import/commit",
        cookies=owner_cookies,
        files={"file": ("agents.csv", _fixture_csv("agents"), "text/csv")},
    )
    assert no_csrf.status_code == 403


def test_preview_does_not_write_and_commit_is_tenant_scoped(app_context):
    cookies, headers = _session(app_context, app_context.owner)
    preview = app_context.client.post(
        "/app/import/preview",
        cookies=cookies,
        headers=headers,
        files={"file": ("agents.csv", _fixture_csv("agents"), "text/csv")},
    )
    assert preview.status_code == 200
    assert preview.json()["ok"] is True
    assert preview.json()["batch_id"] is None
    assert app_context.conn.execute("SELECT count(*) FROM import_batches").fetchone()[0] == 0

    committed = app_context.client.post(
        "/app/import/commit",
        cookies=cookies,
        headers=headers,
        files={"file": ("agents.csv", _fixture_csv("agents"), "text/csv")},
    )
    assert committed.status_code == 200
    batch_id = committed.json()["batch_id"]
    assert (
        app_context.conn.execute("SELECT tenant_id FROM imported_rows").fetchone()["tenant_id"]
        == "tenant-cc"
    )

    other_cookies, _ = _session(app_context, app_context.other_owner)
    hidden = app_context.client.get(f"/app/import/{batch_id}", cookies=other_cookies)
    assert hidden.status_code == 404
    visible = app_context.client.get(f"/app/import/{batch_id}", cookies=cookies)
    assert visible.status_code == 200
    assert visible.json()["provenance_data_mode"] == "simulated_realistic"


def test_wrong_fixture_tenant_is_quarantined_without_rows(app_context):
    cookies, headers = _session(app_context, app_context.owner)
    response = app_context.client.post(
        "/app/import/commit",
        cookies=cookies,
        headers=headers,
        files={"file": ("athletes.csv", _fixture_csv("athletes"), "text/csv")},
    )

    assert response.status_code == 422
    report = response.json()
    assert report["ok"] is False
    assert report["errors"][0]["code"] == "tenant_profile"
    batch = app_context.client.get(f"/app/import/{report['batch_id']}", cookies=cookies)
    assert batch.json()["status"] == "quarantined"
    assert app_context.conn.execute("SELECT count(*) FROM imported_rows").fetchone()[0] == 0


def test_discard_is_tenant_scoped_and_audited(app_context):
    cookies, headers = _session(app_context, app_context.owner)
    response = app_context.client.post(
        "/app/import/commit",
        cookies=cookies,
        headers=headers,
        files={"file": ("agents.csv", _fixture_csv("agents"), "text/csv")},
    )
    batch_id = response.json()["batch_id"]
    other_cookies, other_headers = _session(app_context, app_context.other_owner)

    refused = app_context.client.post(
        f"/app/import/{batch_id}/discard",
        cookies=other_cookies,
        headers=other_headers,
    )
    assert refused.status_code == 404

    discarded = app_context.client.post(
        f"/app/import/{batch_id}/discard",
        cookies=cookies,
        headers=headers,
    )
    assert discarded.status_code == 200
    assert app_context.conn.execute("SELECT count(*) FROM imported_rows").fetchone()[0] == 0
    assert (
        app_context.conn.execute(
            "SELECT count(*) FROM nodes WHERE kind = 'import_batch' AND body LIKE '%discarded%'"
        ).fetchone()[0]
        == 1
    )
