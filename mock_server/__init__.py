"""
Mock server for parallel frontend development against Helix-Codex.

Mirrors the real JSON API surface from both `server/app.py` (Helix Codex OS
spine) and `helix_codex_app/app.py` (product shell) so a frontend can develop
without the governed engine, SQLite stores, or auth pipeline running.

Run standalone:
    python -m mock_server            # uvicorn on :8001, scenario=default
    MOCK_SCENARIO=errors python -m mock_server

Or use the pytest fixtures in tests/mock_server/conftest.py.
"""
from __future__ import annotations

from .server import create_mock_app

__all__ = ["create_mock_app"]
