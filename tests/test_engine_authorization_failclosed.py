"""Engine-level authorisation must fail closed.

A request whose role does not own the capability is refused by
`security.policy.authorize`. That is only a control if the adapter acts on the
refusal. `engines/wfm/adapter.py` did not: its denial path called `_log` with one
argument too many, the resulting `TypeError` was swallowed by the surrounding
`except Exception`, and `adapt(...)` returned `error=None` for an unknown role.

These tests pin the behaviour for all six adapters, so the same defect in any one
of them fails here rather than passing as a successful run.
"""

from __future__ import annotations

import pytest

from engines.b2b.adapter import adapt as b2b_adapt
from engines.contracts import ENGINE_BASELINE_PAYLOADS
from engines.crm.adapter import adapt as crm_adapt
from engines.cx.adapter import adapt as cx_adapt
from engines.personnel.adapter import adapt as personnel_adapt
from engines.rta.adapter import adapt as rta_adapt
from engines.wfm.adapter import adapt as wfm_adapt

RTA_PAYLOAD = {
    "schedule_data": {
        "agent_id": ["a1"],
        "scheduled_min": [480],
        "date": ["2026-09-07"],
        "hour": [9],
        "scheduled_hours": [8.0],
    },
    "actual_data": {
        "agent_id": ["a1"],
        "logged_min": [470],
        "productive_min": [450],
        "date": ["2026-09-07"],
        "hour": [9],
        "actual_hours": [7.83],
    },
    "is_sample": True,
}

ADAPTERS = {
    "wfm": (wfm_adapt, ENGINE_BASELINE_PAYLOADS["wfm"]),
    "rta": (rta_adapt, RTA_PAYLOAD),
    "cx": (cx_adapt, ENGINE_BASELINE_PAYLOADS["cx"]),
    "b2b": (b2b_adapt, ENGINE_BASELINE_PAYLOADS["b2b"]),
    "personnel": (personnel_adapt, ENGINE_BASELINE_PAYLOADS["personnel"]),
    "crm": (crm_adapt, ENGINE_BASELINE_PAYLOADS["crm"]),
}


def _call(adapter, payload, role):
    return adapter(
        input_payload=dict(payload),
        tenant_id="tenant-authz",
        client_id="client-authz",
        correlation_id="corr-authz",
        causation_id=None,
        actor=role,
        owning_role_id=role,
        is_sample=True,
    )


@pytest.mark.parametrize("engine", sorted(ADAPTERS))
def test_an_unknown_role_is_denied_by_every_adapter(engine):
    adapter, payload = ADAPTERS[engine]
    result = _call(adapter, payload, "unknown_role")
    assert result.error is not None, f"{engine} allowed a role that owns nothing"
    assert result.error["code"] == "unauthorized"


@pytest.mark.parametrize("engine", sorted(ADAPTERS))
def test_the_owning_role_still_succeeds(engine):
    adapter, payload = ADAPTERS[engine]
    owner = {
        "wfm": "ops_gm",
        "rta": "ops_gm",
        "cx": "ops_gm",
        "b2b": "sales_gm",
        "personnel": "hr_personnel_gm",
        "crm": "sales_gm",
    }[engine]
    result = _call(adapter, payload, owner)
    assert result.error is None, f"{engine} refused its owning role: {result.error}"


def test_the_wfm_denial_path_still_emits_telemetry_arguments():
    """The denial logging call must keep the signature its helper declares.

    `_log(event_type, correlation_id, actor, result_status, **kwargs)` takes four
    positional arguments. The denial path passed five. This asserts the call site
    and the helper cannot silently drift apart again.
    """
    import inspect

    from engines.wfm import adapter as wfm_module

    signature = inspect.signature(wfm_module._log)
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
    ]
    assert len(positional) == 4
