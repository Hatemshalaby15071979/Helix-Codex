"""BLK-021 regression: the ingest engine binds loopback by default.

The engine previously defaulted to ``0.0.0.0`` per a "cockpit deployment spec".
Everything else in the repository binds 127.0.0.1; the ingest engine now does
too. Containers and trusted networks opt in with ``--host 0.0.0.0``.
Also pins the startup warning emitted when the local-dev approve override is on.
"""

from __future__ import annotations

import logging

import ingest_engine


def test_default_bind_is_loopback(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run(app, *, host, port, log_level):  # noqa: ANN001
        captured.update(app=app, host=host, port=port, log_level=log_level)

    monkeypatch.setattr(ingest_engine.uvicorn, "run", _fake_run)
    monkeypatch.setattr("sys.argv", ["ingest_engine.py"])
    ingest_engine.main()
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8000


def test_host_flag_overrides_default(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_run(app, *, host, port, log_level):  # noqa: ANN001
        captured.update(host=host, port=port)

    monkeypatch.setattr(ingest_engine.uvicorn, "run", _fake_run)
    monkeypatch.setattr("sys.argv", ["ingest_engine.py", "--host", "0.0.0.0", "--port", "8010"])
    ingest_engine.main()
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8010


def test_unauthenticated_override_emits_loud_warning(monkeypatch, caplog):
    monkeypatch.setenv("HELIX_COCKPIT_ALLOW_UNAUTHENTICATED", "true")
    with caplog.at_level(logging.WARNING, logger="ingest_engine"):
        ingest_engine._warn_if_unauthenticated_override()
    assert any("must never" in record.message for record in caplog.records)


def test_no_warning_without_override(monkeypatch, caplog):
    monkeypatch.delenv("HELIX_COCKPIT_ALLOW_UNAUTHENTICATED", raising=False)
    with caplog.at_level(logging.WARNING, logger="ingest_engine"):
        ingest_engine._warn_if_unauthenticated_override()
    assert caplog.records == []
