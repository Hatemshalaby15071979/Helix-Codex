"""
API tenant-scope tests for the headless FastAPI surface.

Every bearer token is bound to a tenant scope (HELIX_API_TOKEN_TENANT_ID /
HELIX_API_TOKEN_CLIENT_ID). A scoped token may only read, write, halt, or
inspect inside its own scope: any request value naming another tenant or
client is refused, and omitted values default to the identity scope rather
than to a caller-chosen tenant. A global operator exists only with the
explicit HELIX_API_ALLOW_GLOBAL_OPERATOR flag for a universal-approver role,
and every global access is audited.

The cross-tenant tests below are the can-fail proof for this file: they pass
only while the route-level require_tenant / require_client calls are in
place. test_scope_enforcement_is_load_bearing demonstrates the sensitivity
directly by disabling the enforcement point and observing the leak.
"""

from __future__ import annotations

import secrets

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
TestClient = fastapi_testclient.TestClient

TOKEN = secrets.token_urlsafe(24)
TENANT_A = "tenant-scope-a"
TENANT_B = "tenant-scope-b"
CLIENT_A = "client-scope-a"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("HELIX_API_TOKEN", TOKEN)
    monkeypatch.setenv("HELIX_API_TOKEN_ROLE", "sami")
    monkeypatch.setenv("HELIX_API_TOKEN_TENANT_ID", TENANT_A)
    monkeypatch.setenv("HELIX_API_TOKEN_CLIENT_ID", CLIENT_A)
    monkeypatch.delenv("HELIX_API_ALLOW_GLOBAL_OPERATOR", raising=False)
    from server.app import create_app
    from server.config import Settings

    settings = Settings(
        profile="local",
        db_path=str(tmp_path / "workflow.db"),
        audit_db_path=str(tmp_path / "audit.db"),
        log_path=str(tmp_path / "logs.jsonl"),
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def _auth():
    return {"Authorization": f"Bearer {TOKEN}"}


def _as_tenant(monkeypatch, tenant, client=CLIENT_A):
    monkeypatch.setenv("HELIX_API_TOKEN_TENANT_ID", tenant)
    monkeypatch.setenv("HELIX_API_TOKEN_CLIENT_ID", client)


def _workflow_payload(tenant, client=CLIENT_A):
    return {
        "tenant_id": tenant,
        "client_id": client,
        "capability": "wfm_forecast",
        "requesting_actor": "suby",
        "owning_role_id": "ops_gm",
        "input_payload": {"arrival_rate": 10},
        "requires_approval": True,
    }


def test_scoped_token_cannot_read_another_tenant(client, monkeypatch):
    created = client.post("/api/docs/", params={"title": "a-doc"}, headers=_auth())
    assert created.status_code == 200
    doc_id = created.json()["node_id"]
    mine = client.get("/api/docs/", headers=_auth()).json()
    assert any(d["node_id"] == doc_id for d in mine)
    _as_tenant(monkeypatch, TENANT_B)
    foreign_list = client.get("/api/docs/", headers=_auth()).json()
    assert all(d["tenant_id"] != TENANT_A for d in foreign_list)
    assert client.get(f"/api/docs/{doc_id}", headers=_auth()).status_code == 404
    leaked = client.get(f"/api/docs/{doc_id}", params={"tenant_id": TENANT_A}, headers=_auth())
    assert leaked.status_code == 403


def test_scoped_token_cannot_write_another_tenant(client):
    assert (
        client.post(
            "/api/docs/", params={"title": "x", "tenant_id": TENANT_B}, headers=_auth()
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/tasks/", params={"title": "x", "tenant_id": TENANT_B}, headers=_auth()
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/chat/messages",
            params={"message": "hi", "tenant_id": TENANT_B},
            headers=_auth(),
        ).status_code
        == 403
    )
    denied = client.post("/api/workflows", json=_workflow_payload(TENANT_B), headers=_auth())
    assert denied.status_code == 403


def test_scoped_token_cannot_inspect_another_tenants_halt_state(client):
    assert (
        client.get("/api/halt/status", params={"tenant_id": TENANT_B}, headers=_auth()).status_code
        == 403
    )
    assert (
        client.post(
            "/api/halt/engage",
            json={"reason": "cross-tenant drill", "tenant_id": TENANT_B},
            headers=_auth(),
        ).status_code
        == 403
    )
    own = client.get("/api/halt/status", headers=_auth())
    assert own.status_code == 200
    assert own.json()["engaged"] is False


def test_global_operator_requires_explicit_configuration(client, monkeypatch):
    monkeypatch.delenv("HELIX_API_TOKEN_TENANT_ID", raising=False)
    monkeypatch.delenv("HELIX_API_TOKEN_CLIENT_ID", raising=False)
    assert client.get("/api/approvals", headers=_auth()).status_code == 500
    monkeypatch.setenv("HELIX_API_ALLOW_GLOBAL_OPERATOR", "true")
    assert client.get("/api/approvals", headers=_auth()).status_code == 200
    monkeypatch.setenv("HELIX_API_TOKEN_ROLE", "ops_gm")
    assert client.get("/api/approvals", headers=_auth()).status_code == 500


def test_unknown_or_missing_scope_fails_closed(client, monkeypatch):
    monkeypatch.delenv("HELIX_API_TOKEN_TENANT_ID", raising=False)
    monkeypatch.delenv("HELIX_API_TOKEN_CLIENT_ID", raising=False)
    assert client.get("/api/approvals", headers=_auth()).status_code == 500
    assert client.post("/api/docs/", params={"title": "x"}, headers=_auth()).status_code == 500
    monkeypatch.setenv("HELIX_API_TOKEN_TENANT_ID", "")
    assert client.get("/api/approvals", headers=_auth()).status_code == 500
    monkeypatch.delenv("HELIX_API_TOKEN_TENANT_ID", raising=False)
    monkeypatch.setenv("HELIX_API_TOKEN_CLIENT_ID", "orphan-client")
    assert client.get("/api/approvals", headers=_auth()).status_code == 500


def test_health_endpoints_remain_public(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_omitted_tenant_defaults_to_identity_scope(client, monkeypatch):
    created = client.post("/api/docs/", params={"title": "scoped-doc"}, headers=_auth())
    assert created.status_code == 200
    doc_id = created.json()["node_id"]
    stored = client.get(f"/api/docs/{doc_id}", headers=_auth()).json()
    assert stored["tenant_id"] == TENANT_A
    _as_tenant(monkeypatch, TENANT_B)
    assert client.get(f"/api/docs/{doc_id}", headers=_auth()).status_code == 404
    assert client.get("/api/docs/", headers=_auth()).json() == []


@pytest.mark.parametrize(
    ("create_path", "create_params", "list_path", "body_key"),
    [
        ("/api/docs/", {"title": "Synthetic tenant record"}, "/api/docs/", "title"),
        ("/api/tasks/", {"title": "Synthetic tenant record"}, "/api/tasks/", "title"),
        (
            "/api/chat/messages",
            {"message": "Synthetic tenant record"},
            "/api/chat/messages",
            "content",
        ),
    ],
)
def test_concurrent_tenant_writes_keep_distinct_records(
    client, monkeypatch, create_path, create_params, list_path, body_key
):
    created_a = client.post(create_path, params=create_params, headers=_auth())
    assert created_a.status_code == 200
    node_a = created_a.json()["node_id"]

    _as_tenant(monkeypatch, TENANT_B, client="client-scope-b")
    created_b = client.post(create_path, params=create_params, headers=_auth())
    assert created_b.status_code == 200
    node_b = created_b.json()["node_id"]
    assert node_b != node_a

    rows_b = client.get(list_path, headers=_auth()).json()
    assert {row["node_id"] for row in rows_b} == {node_b}
    assert rows_b[0]["body"][body_key] == create_params[next(iter(create_params))]
    assert client.get(f"{list_path}{node_a}", headers=_auth()).status_code in {404, 405}

    _as_tenant(monkeypatch, TENANT_A)
    rows_a = client.get(list_path, headers=_auth()).json()
    assert {row["node_id"] for row in rows_a} == {node_a}
    assert rows_a[0]["body"][body_key] == create_params[next(iter(create_params))]


def test_workflows_and_approvals_are_scope_safe(client, monkeypatch):
    submitted = client.post("/api/workflows", json=_workflow_payload(TENANT_A), headers=_auth())
    assert submitted.status_code == 409
    workflow_id = submitted.json()["workflow_id"]
    queue = client.get("/api/approvals", headers=_auth()).json()
    assert any(item["workflow_id"] == workflow_id for item in queue)
    _as_tenant(monkeypatch, TENANT_B)
    assert client.get("/api/approvals", headers=_auth()).json() == []
    assert client.get(f"/api/workflows/{workflow_id}", headers=_auth()).status_code == 404
    foreign_decide = client.post(
        f"/api/approvals/{workflow_id}",
        json={
            "approver_actor": "andy",
            "approver_role_id": "compliance_quality_gm",
            "decision": "approved",
            "reason": "cross-tenant decide must not land",
        },
        headers=_auth(),
    )
    assert foreign_decide.status_code == 404
    _as_tenant(monkeypatch, TENANT_A)
    assert client.get(f"/api/workflows/{workflow_id}", headers=_auth()).status_code == 200


def test_global_access_is_audited(client, monkeypatch, tmp_path):
    monkeypatch.delenv("HELIX_API_TOKEN_TENANT_ID", raising=False)
    monkeypatch.delenv("HELIX_API_TOKEN_CLIENT_ID", raising=False)
    monkeypatch.setenv("HELIX_API_ALLOW_GLOBAL_OPERATOR", "true")
    resp = client.get("/api/halt/status", params={"tenant_id": TENANT_A}, headers=_auth())
    assert resp.status_code == 200
    import json as _json

    log_path = tmp_path / "logs.jsonl"
    entries = [_json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    access = [e for e in entries if e.get("event_type") == "global_scope_access"]
    assert access, "global halt-status read was not audited"
    first = access[0]
    assert first["actor"]
    assert first["tenant_id"] == TENANT_A
    assert "GET /api/halt/status" in str(first.get("payload", {}).get("route", ""))
    assert first.get("correlation_id")


def test_scope_enforcement_is_load_bearing(client, monkeypatch):
    created = client.post("/api/docs/", params={"title": "a-doc"}, headers=_auth())
    assert created.status_code == 200
    _as_tenant(monkeypatch, TENANT_B)
    assert client.get("/api/docs/", headers=_auth()).json() == []

    def _passthrough(identity, requested, **kwargs):
        return requested

    monkeypatch.setattr("server.scope.require_tenant", _passthrough)
    leaked = client.get("/api/docs/", params={"tenant_id": TENANT_A}, headers=_auth())
    assert leaked.status_code == 200
    assert any(d["tenant_id"] == TENANT_A for d in leaked.json())
