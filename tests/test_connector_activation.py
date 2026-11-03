"""BLK-014 regression: the write gate reads real activation status.

The governance gate used to receive ``provider_activated=True`` as a constant,
so an unactivated or disconnected provider could pass it. Activation now comes
from the connector's own status (AUTHENTICATED/HEALTHY, or an explicit
``is_activated`` declaration); anything unreadable fails closed.
"""

from __future__ import annotations

from connectors.contracts import ConnectorContext, ConnectorStatus
from connectors.fakes import FakeConnector
from connectors.gateway import ConnectorGateway, _provider_activated


def _context(data_mode: str = "live_external") -> ConnectorContext:
    return ConnectorContext(
        tenant_id="tenant_a",
        organization_id="org_1",
        client_id="client_1",
        actor="test_actor",
        correlation_id="corr_activation",
        data_mode=data_mode,
    )


def _intent() -> dict:
    return {"capability_id": "write_local.account", "payload": {"account_id": "a1"}}


def test_unconfigured_and_dead_statuses_are_not_activated() -> None:
    for status in (
        ConnectorStatus.UNCONFIGURED,
        ConnectorStatus.CONFIGURED,
        ConnectorStatus.DEGRADED,
        ConnectorStatus.REVOKED,
        ConnectorStatus.DISCONNECTED,
    ):
        connector = FakeConnector(
            connector_id="c",
            provider="fake",
            status=status,
        )
        assert _provider_activated(connector) is False, status


def test_authenticated_and_healthy_are_activated() -> None:
    for status in (ConnectorStatus.AUTHENTICATED, ConnectorStatus.HEALTHY):
        connector = FakeConnector(
            connector_id="c",
            provider="fake",
            status=status,
        )
        assert _provider_activated(connector) is True, status


def test_explicit_is_activated_declaration_wins() -> None:
    connector = FakeConnector(connector_id="c", provider="fake", status=ConnectorStatus.HEALTHY)
    connector.is_activated = False
    assert _provider_activated(connector) is False
    connector.is_activated = True
    assert _provider_activated(connector) is True


def test_unknown_status_object_fails_closed() -> None:
    class _Weird:
        status = object()

    assert _provider_activated(_Weird()) is False


def test_disconnected_provider_plan_requires_approval() -> None:
    gateway = ConnectorGateway()
    gateway.register(
        FakeConnector(
            connector_id="dead",
            provider="fake",
            status=ConnectorStatus.DISCONNECTED,
        )
    )
    plan = gateway.plan_write(connector_id="dead", intent=_intent(), context=_context())
    assert plan.requires_approval is True
