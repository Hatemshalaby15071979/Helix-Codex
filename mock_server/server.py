"""
Mock server application factory.

Builds a FastAPI app that mirrors the Helix-Codex JSON API surface, with
middleware that applies the active scenario (latency, error injection, request
tracking) and swappable scenario state. Auth is intentionally bypassed: any
request is treated as an authenticated demo account so frontend dev never needs
the real Supabase / session pipeline.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import routers
from .scenarios import DEFAULT_SCENARIO, SCENARIOS, Scenario, get_scenario
from .state import MockState


def create_mock_app(scenario: str | None = None) -> FastAPI:
    """Create the mock FastAPI app.

    ``scenario`` overrides the MOCK_SCENARIO env var (default: "default").
    """
    initial = scenario or os.getenv("MOCK_SCENARIO", DEFAULT_SCENARIO)
    if initial not in SCENARIOS:
        initial = DEFAULT_SCENARIO

    state = MockState()

    app = FastAPI(title="Helix Codex Mock Server", version="0.9.0-mock")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Per-process active scenario, switchable at runtime.
    app.state.scenario_name = initial
    app.state.state = state
    # request counter for the errors scenario rate limit
    app.state.rate_counter = 0

    def current_scenario() -> Scenario:
        return get_scenario(app.state.scenario_name)

    @app.middleware("http")
    async def scenario_middleware(request: Request, call_next):
        scen = current_scenario()
        # latency simulation
        if scen.latency_ms:
            await asyncio.sleep(scen.latency_ms / 1000.0)
        # synthetic 500 injection
        if scen.error_rate and uuid.uuid4().int % 100 < int(scen.error_rate * 100):
            return JSONResponse({"error": "mock injected failure"}, status_code=500)
        # rate-limit simulation (errors scenario)
        if scen.rate_limit:
            limit = scen.rate_limit.get("*", scen.rate_limit.get(str(request.url.path), 0))
            if limit:
                app.state.rate_counter += 1
                if app.state.rate_counter > limit:
                    resp = JSONResponse(
                        {"error": "Rate limit exceeded", "retry_after": 1}, status_code=429
                    )
                    resp.headers["Retry-After"] = "1"
                    resp.headers["X-Mock-Server"] = "true"
                    resp.headers["X-Mock-Scenario"] = app.state.scenario_name
                    return resp
        response = await call_next(request)
        response.headers["X-Mock-Server"] = "true"
        response.headers["X-Mock-Scenario"] = app.state.scenario_name
        state.log_request(request.method, str(request.url.path), response.status_code)
        return response

    # Runtime scenario switch (no restart needed).
    @app.post("/__mock/scenario/{name}")
    async def set_scenario(name: str) -> JSONResponse:
        if name not in SCENARIOS:
            return JSONResponse(
                {"error": f"unknown scenario {name!r}", "available": list(SCENARIOS)},
                status_code=400,
            )
        app.state.scenario_name = name
        app.state.rate_counter = 0
        return JSONResponse({"scenario": name})

    @app.get("/__mock/scenario")
    def get_scenario_endpoint() -> JSONResponse:
        return JSONResponse(
            {"scenario": app.state.scenario_name, "available": list(SCENARIOS)}
        )

    routers.register_routes(app, state, current_scenario)
    return app


# Allow `from mock_server.server import create_mock_app` callers to switch.
def set_scenario(app: FastAPI, name: str) -> None:
    app.state.scenario_name = name
