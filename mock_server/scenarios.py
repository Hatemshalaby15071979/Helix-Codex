"""
Scenario definitions for the mock server.

A scenario changes latency, error injection, and whether the store is stateful.
Frontend devs switch scenarios with the MOCK_SCENARIO env var or the
X-Mock-Scenario header, or by calling POST /__mock/scenario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scenario:
    name: str
    description: str
    # base latency added to every response, in milliseconds
    latency_ms: int = 0
    # chance [0,1] of returning a synthetic 500
    error_rate: float = 0.0
    # if True, writes mutate MockState; if False, writes are accepted (202) but
    # not persisted — useful for deterministic UI demos.
    stateful: bool = True
    # per-endpoint forced overrides, e.g. {"GET /healthz": 503}
    forced_status: dict[str, int] = field(default_factory=dict)
    # rate-limit behaviour
    rate_limit: dict[str, int] = field(default_factory=dict)


SCENARIOS: dict[str, Scenario] = {
    "default": Scenario(
        name="default",
        description="Happy-path parallel development: realistic data, fast, stateful.",
        latency_ms=20,
        stateful=True,
    ),
    "errors": Scenario(
        name="errors",
        description="Surfaces error paths: 404s on missing ids, 429 after N calls, 503 on halt.",
        latency_ms=20,
        stateful=True,
        rate_limit={"*": 25},  # 429 after 25 requests
    ),
    "degraded": Scenario(
        name="degraded",
        description="Slow network simulation for loading states and timeouts.",
        latency_ms=1500,
        stateful=True,
    ),
    "readonly": Scenario(
        name="readonly",
        description="Deterministic demo: reads work, writes return 202 but are not persisted.",
        latency_ms=20,
        stateful=False,
    ),
}

DEFAULT_SCENARIO = "default"


def get_scenario(name: str) -> Scenario:
    return SCENARIOS.get(name, SCENARIOS[DEFAULT_SCENARIO])
