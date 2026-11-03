from __future__ import annotations

import json
import os
import pathlib
import socket
import subprocess
import sys
import time

import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _get_json(url: str, timeout: float = 15) -> tuple[int, dict[str, object]]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1, trust_env=False)
            response.raise_for_status()
            body = json.loads(response.text)
            assert isinstance(body, dict)
            return response.status_code, body
        except (OSError, httpx.HTTPError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.1)
    raise AssertionError(f"{url} did not become ready: {last_error}")


def test_local_ready_chain_and_supervised_telemetry(tmp_path: pathlib.Path):
    api_port, ingest_port = _free_port(), _free_port()
    while ingest_port == api_port:
        ingest_port = _free_port()

    env = os.environ.copy()
    env.pop("HELIX_COCKPIT_ALLOW_UNAUTHENTICATED", None)
    env.update(
        {
            "HELIX_ENV": "local",
            "HELIX_SAMPLE_DATA_MODE": "false",
            "HELIX_DB_PATH": str(tmp_path / "workflow.db"),
            "HELIX_AUDIT_DB_PATH": str(tmp_path / "audit.db"),
        }
    )
    api_log = (tmp_path / "api.log").open("w+")
    ingest_log = (tmp_path / "ingest.log").open("w+")
    processes: list[subprocess.Popen[bytes]] = []
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "server.app:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                ],
                cwd=ROOT,
                env=env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
            )
        )
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "ingest_engine.py",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(ingest_port),
                ],
                cwd=ROOT,
                env=env,
                stdout=ingest_log,
                stderr=subprocess.STDOUT,
            )
        )

        ready_status, ready = _get_json(f"http://127.0.0.1:{api_port}/readyz")
        ingest_status, ingest = _get_json(f"http://127.0.0.1:{ingest_port}/healthz")
        supervisor = subprocess.run(
            [
                sys.executable,
                "supervisor.py",
                "--endpoint",
                f"http://127.0.0.1:{ingest_port}/api/v1/telemetry",
                "--ticks",
                "3",
                "--spike-after",
                "2",
                "--tick-seconds",
                "0.01",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert ready_status == 200
        assert ready["ready"] is True
        assert ready["checks"]["audit_chain"] is True
        assert ingest_status == 200
        assert ingest["status"] == "ok"
        assert supervisor.returncode == 0, supervisor.stderr
        assert "delivered=3 dropped=0" in supervisor.stderr
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        api_log.close()
        ingest_log.close()
