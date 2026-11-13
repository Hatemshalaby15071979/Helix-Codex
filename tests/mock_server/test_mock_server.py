"""
Contract tests for the mock server itself — guarantees the mock keeps mirroring
the real API surface the frontend depends on. These run with no database and no
engine, so they are fast unit tests.
"""
from __future__ import annotations

import pytest


def test_health_contract(mock_client):
    r = mock_client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.9.0"
    assert r.headers["X-Mock-Server"] == "true"


def test_workflow_submit_awaiting_approval(mock_client):
    # Requires approval -> 409 with awaiting_approval state, appears in queue.
    r = mock_client.post(
        "/api/workflows",
        json={"capability": "wfm_forecast", "tenant_id": "t", "client_id": "c", "requires_approval": True},
    )
    assert r.status_code == 409
    assert r.json()["state"] == "awaiting_approval"

    q = mock_client.get("/api/approvals")
    assert any(w["workflow_id"] == r.json()["workflow_id"] for w in q.json())


def test_workflow_approve_transitions_state(mock_client):
    created = mock_client.post(
        "/api/workflows",
        json={"capability": "x", "tenant_id": "t", "client_id": "c", "requires_approval": True},
    )
    wid = created.json()["workflow_id"]
    decided = mock_client.post(
        f"/api/approvals/{wid}",
        json={"decision": "approved", "approver_actor": "a", "approver_role_id": "owner"},
    )
    assert decided.status_code == 200
    assert decided.json()["state"] == "completed"


def test_task_crud(mock_client):
    created = mock_client.post("/app/api/tasks", json={"title": "Demo", "priority": "high"})
    assert created.status_code == 201
    tid = created.json()["task_id"]

    fetched = mock_client.get(f"/app/api/tasks/{tid}")
    assert fetched.status_code == 200
    assert fetched.json()["task"]["title"] == "Demo"

    # Status changes go through the dedicated POST /status endpoint (matches the
    # real helix_codex_app router; PUT only updates metadata).
    stated = mock_client.post(f"/app/api/tasks/{tid}/status", json={"status": "doing"})
    assert stated.status_code == 200
    assert stated.json()["status"] == "doing"

    commented = mock_client.post(f"/app/api/tasks/{tid}/comments", json={"body": "note"})
    assert commented.status_code == 201

    missing = mock_client.get("/app/api/tasks/does-not-exist")
    assert missing.status_code == 404


def test_event_creation_uses_real_shape(mock_client):
    r = mock_client.post(
        "/app/api/events",
        json={
            "title": "Standup",
            "starts_at": "2026-01-01T09:00:00+00:00",
            "ends_at": "2026-01-01T10:00:00+00:00",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["attendees"][0]["account_id"] == "account_demo"


def test_memory_proposal_lifecycle(mock_client):
    created = mock_client.post("/app/api/memory/proposals", json={"kind": "policy", "target": "wfm"})
    pid = created.json()["proposal_id"]
    assert created.status_code == 201
    assert created.json()["state"] == "draft"

    assert mock_client.post(f"/app/api/memory/proposals/{pid}/evaluate").status_code == 200
    approved = mock_client.post(f"/app/api/memory/proposals/{pid}/approve")
    assert approved.status_code == 200
    assert approved.json()["state"] == "approved"


def test_scenario_switch(mock_client):
    assert mock_client.get("/__mock/scenario").json()["scenario"] == "default"
    switched = mock_client.post("/__mock/scenario/degraded")
    assert switched.status_code == 200
    assert switched.json()["scenario"] == "degraded"
    assert mock_client.get("/healthz").headers["X-Mock-Scenario"] == "degraded"

    unknown = mock_client.post("/__mock/scenario/bogus")
    assert unknown.status_code == 400


def test_reset_clears_state(mock_client):
    mock_client.post("/app/api/tasks", json={"title": "temp"})
    before = len(mock_client.get("/app/api/tasks").json())
    assert before >= 1
    mock_client.post("/__mock/reset")
    # seed had 3 tasks; after reset we are back to exactly the seed set
    assert len(mock_client.get("/app/api/tasks").json()) == 3


def test_rate_limit_in_errors_scenario(mock_client_errors):
    # errors scenario limits "*" to 25 requests; exceed it.
    last = None
    for _ in range(30):
        last = mock_client_errors.get("/healthz")
    assert last.status_code == 429
    assert last.headers.get("Retry-After") == "1"
