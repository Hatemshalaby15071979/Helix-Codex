"""Driver-level tenant isolation attack suite (BLK-008).

Proves, on synthetic data only, that a foreign tenant cannot read or overwrite
another tenant's rows through the store's public API — the checks happen at SQL
level, not by post-filtering in Python:

* workflows/events carry tenant_id on the row; scoped reads filter at SQL level
  (legacy rows are backfilled on open);
* workflow_tasks already carried tenant_id; scoped reads and fail-closed empty
  tenants are pinned here;
* audit_events has no tenant column (the ledger is shared by design), so scoped
  reads are enforced with an EXISTS subquery against workflow_tasks — rows that
  cannot be tied to the tenant are invisible;
* NodeStore refuses to overwrite a colliding node_id (was INSERT OR REPLACE);
* an empty-string tenant is refused everywhere (fail closed).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from control_plane.store import Store, TenantScopeMissing
from server.models.node import (
    Classification,
    DocumentNode,
    Nature,
    NodeEnvelope,
    Provenance,
)
from server.models.store import NodeExistsError, NodeStore


def _seed_store(store: Store) -> None:
    from contracts.task import CorrelationContext
    from control_plane.events import Event
    from control_plane.workflow import Workflow

    now = datetime.now(timezone.utc).isoformat()
    for wf_id, tenant in (("wf-a", "tenant-a"), ("wf-b", "tenant-b")):
        corr = CorrelationContext(
            correlation_id=f"corr-{tenant}",
            idempotency_key=f"idem-{tenant}",
            tenant_id=tenant,
            client_id=f"client-{tenant}",
            created_at="2026-01-01T00:00:00Z",
        )
        wf = Workflow(
            workflow_id=wf_id,
            idempotency_key=corr.idempotency_key,
            correlation=corr,
            tenant_id=tenant,
            client_id=corr.client_id,
            requesting_actor="actor",
            owning_role_id="role",
            capability="cap",
            state="proposed",
            input_payload={"is_sample": True},
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        store.create_workflow(wf)
        store.append_event(
            Event(
                event_id=f"ev-{tenant}",
                event_type="workflow_created",
                aggregate_id=wf_id,
                correlation_id=corr.correlation_id,
                actor="actor",
                schema_version="1.0",
                timestamp="2026-01-01T00:00:00Z",
                payload={"is_sample": True},
                sequence=0,
            )
        )

    cur = store.conn.cursor()
    for task_id, wf_id, corr, tenant in (
        ("task-a", "wf-a", "corr-a", "tenant-a"),
        ("task-b", "wf-b", "corr-b", "tenant-b"),
    ):
        cur.execute(
            """INSERT INTO workflow_tasks (
                   task_id, workflow_id, correlation_id, tenant_id, client_id,
                   actor_id, actor_role_id, owning_role_id, capability, target_engine,
                   state, estimated_financial_cost, financial_limit_usd, data_classification,
                   confidence_score, reason_code, reason, payload, error, created_at, updated_at, schema_version
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                wf_id,
                corr,
                tenant,
                "client-" + tenant,
                "actor",
                "role",
                "owning",
                "cap",
                None,
                "awaiting_approval",
                0.0,
                None,
                "internal",
                1.0,
                None,
                None,
                "{}",
                None,
                now,
                now,
                "1.0",
            ),
        )
    for event_id, corr, task_id, wf_id, _tenant in (
        ("aud-a", "corr-a", "task-a", "wf-a", "tenant-a"),
        ("aud-b", "corr-b", "task-b", "wf-b", "tenant-b"),
    ):
        cur.execute(
            """INSERT INTO audit_events (
                   event_id, occurred_at, correlation_id, actor_id, actor_role_id,
                   event_type, decision, reason_code, reason, task_id, workflow_id,
                   from_state, to_state, payload, prev_hash, record_hash
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                now,
                corr,
                "actor",
                "role",
                "test_event",
                "approved",
                None,
                None,
                task_id,
                wf_id,
                None,
                None,
                "{}",
                "",
                f"hash-{event_id}",
            ),
        )
    store.conn.commit()


@pytest.fixture()
def seeded(tmp_path):
    store = Store(db_path=str(tmp_path / "workflow.db"))
    _seed_store(store)
    yield store
    store.close()


def test_scoped_workflow_read_is_invisible_to_foreign_tenant(seeded):
    assert seeded.get_workflow_scoped("wf-a", "tenant-a") is not None
    assert seeded.get_workflow_scoped("wf-a", "tenant-b") is None
    assert seeded.get_workflow_scoped("wf-b", "tenant-a") is None


def test_scoped_list_workflows_filters_foreign_rows(seeded):
    assert {w.workflow_id for w in seeded.list_workflows(tenant_id="tenant-a")} == {"wf-a"}
    assert {w.workflow_id for w in seeded.list_workflows(tenant_id="tenant-b")} == {"wf-b"}


def test_scoped_events_read_is_invisible_to_foreign_tenant(seeded):
    assert seeded.get_events_scoped("wf-a", "tenant-a") != []
    assert seeded.get_events_scoped("wf-a", "tenant-b") == []


def test_get_workflow_task_scoped(seeded):
    assert seeded.get_workflow_task("task-a", "tenant-a") is not None
    assert seeded.get_workflow_task("task-a", "tenant-b") is None
    with pytest.raises(TenantScopeMissing):
        seeded.get_workflow_task("task-a", "")


def test_list_workflow_tasks_scoped(seeded):
    scoped = seeded.list_workflow_tasks(state="awaiting_approval", tenant_id="tenant-a")
    assert [t["task_id"] for t in scoped] == ["task-a"]
    with pytest.raises(TenantScopeMissing):
        seeded.list_workflow_tasks(tenant_id="   ")


def test_audit_events_scoped_through_workflow_tasks(seeded):
    scoped = seeded.list_audit_events(tenant_id="tenant-a")
    assert [e["event_id"] for e in scoped] == ["aud-a"]
    scoped_b = seeded.list_audit_events(tenant_id="tenant-b")
    assert [e["event_id"] for e in scoped_b] == ["aud-b"]
    with pytest.raises(TenantScopeMissing):
        seeded.list_audit_events(tenant_id="")


def test_empty_tenant_refused_everywhere(seeded):
    with pytest.raises(TenantScopeMissing):
        seeded.get_workflow_scoped("wf-a", "")
    with pytest.raises(TenantScopeMissing):
        seeded.list_workflows(tenant_id="")
    with pytest.raises(TenantScopeMissing):
        seeded.get_events_scoped("wf-a", "")


def test_backfill_assigns_tenant_from_json(tmp_path):
    path = str(tmp_path / "legacy.db")
    store = Store(db_path=path)
    cur = store.conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    # Simulate a legacy row that predates the migration: tenant_id empty, tenant
    # only present in the JSON payload. The next open backfills it.
    cur.execute(
        "INSERT INTO workflows (workflow_id, idempotency_key, correlation_id, data, updated_at, tenant_id) VALUES (?, ?, ?, ?, ?, '')",
        (
            "wf-legacy",
            "idem-legacy",
            "corr-legacy",
            '{"tenant_id": "tenant-legacy", "correlation": {"tenant_id": "tenant-legacy"}}',
            now,
        ),
    )
    store.conn.commit()
    store.close()
    reopened = Store(db_path=path)
    row = reopened.conn.execute(
        "SELECT tenant_id FROM workflows WHERE workflow_id = 'wf-legacy'"
    ).fetchone()
    reopened.close()
    assert row[0] == "tenant-legacy"


# ── NodeStore: write-path isolation ────────────────────────────────────────


def _node(node_id: str, tenant_id: str) -> DocumentNode:
    return DocumentNode(
        envelope=NodeEnvelope(
            node_id=node_id,
            tenant_id=tenant_id,
            client_id=f"client-{tenant_id}",
            correlation_id=f"corr-{tenant_id}",
            causation_id=None,
            classification=Classification.INTERNAL,
            provenance=Provenance(
                source="attack-suite",
                data_mode="simulated_realistic",
                retrieved_at="",
            ),
            nature=Nature.USER_CLAIM,
            created_by="attack-suite",
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        body={"title": f"node for {tenant_id}"},
    )


@pytest.fixture()
def node_store(tmp_path):
    store = NodeStore(tmp_path / "nodes.db")
    store.connect()
    yield store
    store.close()


def test_node_get_is_tenant_scoped(node_store):
    node_store.create(_node("node-attack-a", "tenant-a"))
    assert node_store.get("node-attack-a", "tenant-a") is not None
    assert node_store.get("node-attack-a", "tenant-b") is None


def test_node_list_is_tenant_scoped(node_store):
    node_store.create(_node("node-attack-a", "tenant-a"))
    node_store.create(_node("node-attack-b", "tenant-b"))
    assert [n.envelope.node_id for n in node_store.list_by_tenant("tenant-a")] == ["node-attack-a"]
    assert [n.envelope.node_id for n in node_store.list_by_tenant("tenant-b")] == ["node-attack-b"]


def test_node_id_collision_across_tenants_refuses_overwrite(node_store):
    node_store.create(_node("node-shared-id", "tenant-a"))
    with pytest.raises(NodeExistsError):
        node_store.create(_node("node-shared-id", "tenant-b"))
    # The original row is untouched.
    kept = node_store.get("node-shared-id", "tenant-a")
    assert kept is not None
    assert kept.body == {"title": "node for tenant-a"}
    assert node_store.get("node-shared-id", "tenant-b") is None


def test_node_id_collision_same_tenant_refuses_overwrite(node_store):
    node_store.create(_node("node-same-tenant", "tenant-a"))
    with pytest.raises(NodeExistsError):
        node_store.create(_node("node-same-tenant", "tenant-a"))
