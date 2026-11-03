from __future__ import annotations

import csv
import io

import pytest

from control_plane.store import TenantScopeMissing
from helix_codex_app import db
from helix_codex_app.modules.imports import schema, service
from helix_codex_app.security.accounts import AccountRepository


@pytest.fixture()
def conn(tmp_path):
    connection = db.connect(db_path=str(tmp_path / "app.db"))
    db._init_schema(connection)
    repo = AccountRepository(connection)
    domain = repo.create_domain(
        "callcenterclient.test",
        tenant_id="tenant-cc",
        client_id="callcenterclient",
    )
    repo.create_account(
        domain.domain_id,
        "owner",
        role_id="owner",
        password_hash="test-only",
    )
    yield connection
    db.close(connection)


def _csv_for(profile: str, *, primary_key: str = "fixture-1") -> bytes:
    table = next(item for item in schema.SCHEMAS if item.tenant_profile == profile)
    values = {table.primary_key[0]: primary_key}
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(table.columns)
    writer.writerow([values.get(column, "") for column in table.columns])
    return output.getvalue().encode("utf-8")


def _import(conn, *, tenant_id: str, client_id: str, raw: bytes, commit: bool = True):
    domain = conn.execute(
        "SELECT domain_id FROM domains WHERE tenant_id = ?",
        (tenant_id,),
    ).fetchone()
    actor = conn.execute(
        "SELECT account_id FROM accounts WHERE domain_id = ?",
        (domain["domain_id"],) if domain else (None,),
    ).fetchone()
    return service.import_bytes(
        conn,
        tenant_id=tenant_id,
        client_id=client_id,
        domain_id=domain["domain_id"] if domain else None,
        filename="fixture.csv",
        raw=raw,
        actor_id=actor["account_id"] if actor else "synthetic-owner",
        commit=commit,
    )


def test_preview_validates_without_persisting(conn):
    report = _import(
        conn,
        tenant_id="tenant-cc",
        client_id="callcenterclient",
        raw=_csv_for("callcenterclient"),
        commit=False,
    )

    assert report.ok
    assert report.rows_loaded == 1
    assert service.list_batches(conn, "tenant-cc") == []


def test_import_records_tenant_provenance_and_audit_node(conn):
    report = _import(
        conn,
        tenant_id="tenant-cc",
        client_id="callcenterclient",
        raw=_csv_for("callcenterclient"),
    )

    assert report.ok
    batch = service.get_batch(conn, "tenant-cc", report.batch_id)
    assert batch is not None
    assert batch["tenant_id"] == "tenant-cc"
    assert batch["provenance_data_mode"] == "simulated_realistic"
    row = conn.execute("SELECT tenant_id FROM imported_rows").fetchone()
    assert row["tenant_id"] == "tenant-cc"
    audit = conn.execute(
        "SELECT provenance_data_mode FROM nodes WHERE kind = 'import_batch'"
    ).fetchone()
    assert audit["provenance_data_mode"] == "simulated_realistic"


def test_reimport_upserts_primary_keys_within_tenant(conn):
    first = _import(
        conn,
        tenant_id="tenant-cc",
        client_id="callcenterclient",
        raw=_csv_for("callcenterclient"),
    )
    second = _import(
        conn,
        tenant_id="tenant-cc",
        client_id="callcenterclient",
        raw=_csv_for("callcenterclient"),
    )

    assert first.ok and second.ok
    assert conn.execute("SELECT count(*) FROM imported_rows").fetchone()[0] == 1
    assert conn.execute("SELECT batch_id FROM imported_rows").fetchone()[0] == second.batch_id


def test_fixture_shape_from_another_tenant_is_quarantined(conn):
    report = _import(
        conn,
        tenant_id="tenant-cc",
        client_id="callcenterclient",
        raw=_csv_for("sportacademyclient"),
    )

    assert not report.ok
    assert any(error["code"] == "tenant_profile" for error in report.errors)
    assert conn.execute("SELECT count(*) FROM imported_rows").fetchone()[0] == 0
    assert service.get_batch(conn, "tenant-cc", report.batch_id)["status"] == "quarantined"


def test_invalid_shape_is_quarantined_without_partial_rows(conn):
    raw = b"agent_id,unexpected\nagent-1,value\n"
    report = _import(
        conn,
        tenant_id="tenant-cc",
        client_id="callcenterclient",
        raw=raw,
    )

    assert not report.ok
    assert any(error["code"] == "schema" for error in report.errors)
    assert conn.execute("SELECT count(*) FROM imported_rows").fetchone()[0] == 0
    assert service.get_batch(conn, "tenant-cc", report.batch_id)["status"] == "quarantined"


def test_empty_tenant_scope_is_rejected(conn):
    with pytest.raises(TenantScopeMissing):
        _import(
            conn,
            tenant_id=" ",
            client_id="callcenterclient",
            raw=_csv_for("callcenterclient"),
        )
    with pytest.raises(TenantScopeMissing):
        service.list_batches(conn, "")
    with pytest.raises(TenantScopeMissing):
        service.get_batch(conn, "", "batch-1")


def test_batch_reads_and_discard_are_tenant_scoped(conn):
    report = _import(
        conn,
        tenant_id="tenant-cc",
        client_id="callcenterclient",
        raw=_csv_for("callcenterclient"),
    )

    assert service.get_batch(conn, "tenant-other", report.batch_id) is None
    assert service.list_batches(conn, "tenant-other") == []
    assert not service.discard_batch(
        conn,
        tenant_id="tenant-other",
        batch_id=report.batch_id,
        actor_id="other-owner",
    )
    assert conn.execute("SELECT count(*) FROM imported_rows").fetchone()[0] == 1
