"""
Pytest fixtures for the Helix-Codex mock server.

Use these in frontend/integration tests that need the API contract but not the
governed engine. The mock imports nothing from the real app's auth, stores, or
engines, so it starts in milliseconds and needs no database.

    import pytest

    def test_tasks_flow(mock_client):
        r = mock_client.post("/app/api/tasks", json={"title": "x"})
        assert r.status_code == 201
        tid = r.json()["task_id"]
        assert mock_client.get(f"/app/api/tasks/{tid}").status_code == 200

The ``mock_server`` package lives at the repo root and is importable because
pyproject's ``pythonpath = ["."]`` is set (or you ran pytest from the root).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mock_server.scenarios import DEFAULT_SCENARIO
from mock_server.server import create_mock_app


@pytest.fixture
def mock_app():
    """A fresh mock app with default scenario state."""
    return create_mock_app(DEFAULT_SCENARIO)


@pytest.fixture
def mock_client(mock_app):
    """TestClient bound to a fresh mock app."""
    return TestClient(mock_app)


@pytest.fixture
def mock_client_errors():
    """TestClient running the 'errors' scenario (rate-limited, 404-heavy)."""
    return TestClient(create_mock_app("errors"))


@pytest.fixture
def mock_client_degraded():
    """TestClient running the 'degraded' scenario (high latency)."""
    return TestClient(create_mock_app("degraded"))
