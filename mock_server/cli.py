"""Standalone entry point: `python -m mock_server`."""
from __future__ import annotations

import os

import uvicorn

from .server import create_mock_app


def main() -> None:
    port = int(os.getenv("MOCK_PORT", "8001"))
    scenario = os.getenv("MOCK_SCENARIO", "default")
    app = create_mock_app(scenario)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
