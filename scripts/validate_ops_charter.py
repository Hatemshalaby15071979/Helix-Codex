#!/usr/bin/env python3
"""Validate the shape and non-human status of the simulation operations charter."""

from __future__ import annotations

import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHARTER_PATH = ROOT / "ops" / "ops-charter.yaml"
REQUIRED_ROLES = {"incident_coordinator", "backup_operator"}


def validate() -> list[str]:
    data = yaml.safe_load(CHARTER_PATH.read_text(encoding="utf-8"))
    errors = []
    if not isinstance(data, dict) or data.get("simulation") is not True:
        return ["charter must be an explicit simulation"]
    disclosure = data.get("disclosure")
    if not isinstance(disclosure, str) or "SIMULATION ONLY" not in disclosure:
        errors.append("simulation disclosure is missing")
    roles = data.get("roles")
    if not isinstance(roles, dict) or set(roles) != REQUIRED_ROLES:
        errors.append("required simulated roles are missing or unexpected roles exist")
    elif any(
        not isinstance(role, dict)
        or role.get("assigned_person") is not None
        or role.get("simulated") is not True
        for role in roles.values()
    ):
        errors.append("charter must not assign or imply real people")
    on_call = data.get("on_call")
    if (
        not isinstance(on_call, dict)
        or on_call.get("active") is not False
        or on_call.get("real_person_paged") is not False
        or on_call.get("pager") != "local-test-only"
    ):
        errors.append("charter must disclose that no real on-call or pager exists")
    return errors


def main() -> int:
    errors = validate()
    print(
        json.dumps(
            {
                "simulation": True,
                "disclosure": "SIMULATION ONLY; no human operator is assigned.",
                "ok": not errors,
                "errors": errors,
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
