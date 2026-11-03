"""Tenant-scoped CSV import service for curated fixture exports.

One import = one file = one table of one tenant. All-or-nothing inside a
transaction; partial loads never persist. A file that fails validation is
"quarantined" (a batch row records the reasons) and its rows are never
written. Re-uploading the same export is idempotent per primary key: the
tenant's staged rows are replaced in place, never duplicated.

Everything written here is provenance-labelled ``simulated_realistic`` in this
environment; the importer never treats synthetic data as live.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import pathlib
import re
import sqlite3
import uuid
from dataclasses import dataclass, field
from typing import Any

from helix_codex_app.integration.control_plane_bridge import TenantScopeMissing
from helix_codex_app.modules.imports import schema as schemas

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$")
BOOL_RE = re.compile(r"^(0|1|true|false|yes|no)$", re.IGNORECASE)
MAX_ERRORS = 25


@dataclass
class ImportReport:
    ok: bool
    table_name: str | None = None
    tenant_profile: str | None = None
    rows_total: int = 0
    rows_loaded: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    batch_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "table_name": self.table_name,
            "tenant_profile": self.tenant_profile,
            "rows_total": self.rows_total,
            "rows_loaded": self.rows_loaded,
            "errors": self.errors,
            "batch_id": self.batch_id,
        }


def _err(errors: list[dict[str, Any]], line: int | None, code: str, message: str) -> None:
    if len(errors) < MAX_ERRORS:
        errors.append({"line": line, "code": code, "message": message})


def _parse_csv(raw: bytes) -> tuple[list[str], list[list[str]], list[dict[str, Any]]]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [], [], [{"line": None, "code": "encoding", "message": "file is not valid UTF-8"}]
    try:
        rows = list(csv.reader(io.StringIO(text), strict=True))
    except csv.Error as exc:
        return [], [], [{"line": None, "code": "csv", "message": f"invalid CSV: {exc}"}]
    if not rows:
        return [], [], [{"line": None, "code": "empty", "message": "file is empty"}]
    header = [(h or "").strip() for h in rows[0]]
    if len(set(header)) != len(header):
        dupes = sorted({h for h in header if header.count(h) > 1})
        return (
            [],
            [],
            [{"line": 1, "code": "duplicate_header", "message": f"duplicate columns: {dupes}"}],
        )
    return header, rows[1:], []


def _check_cell(
    col: str,
    value: str,
    table: schemas.TableSchema,
    errors: list[dict[str, Any]],
    line: int | None,
) -> None:
    cell = value.strip()
    if cell == "":
        if col in table.primary_key:
            _err(errors, line, "pk_missing", f"primary key column {col!r} is empty")
        return
    if col in table.numeric:
        try:
            float(cell)
        except ValueError:
            _err(errors, line, "numeric", f"column {col!r} is not a number: {cell[:40]!r}")
    elif col in table.dates:
        if not DATE_RE.match(cell):
            _err(errors, line, "date", f"column {col!r} is not an ISO date/datetime: {cell[:40]!r}")
    elif col in table.booleans:
        if not BOOL_RE.match(cell):
            _err(errors, line, "boolean", f"column {col!r} is not 0/1/true/false: {cell[:40]!r}")


def validate(
    raw: bytes,
) -> tuple[schemas.TableSchema | None, list[dict[str, str]], list[dict[str, Any]]]:
    """Parse and validate. Returns (schema, row_dicts, errors)."""
    errors: list[dict[str, Any]] = []
    header, body, parse_errors = _parse_csv(raw)
    errors.extend(parse_errors)
    if parse_errors:
        return None, [], errors

    table = schemas.detect(header)
    if table is None:
        _err(errors, 1, "schema", f"unrecognised export shape; {schemas.nearest_miss(header)}")
        return None, [], errors

    if len(body) > schemas.MAX_ROWS:
        _err(
            errors,
            None,
            "too_many_rows",
            f"{len(body)} data rows exceed the {schemas.MAX_ROWS} row cap",
        )

    width_bad = next((i + 2 for i, r in enumerate(body) if len(r) != len(header)), None)
    if width_bad is not None:
        _err(errors, width_bad, "row_width", f"row does not have {len(header)} columns")

    row_dicts: list[dict[str, str]] = []
    pk_seen: dict[tuple[str, ...], int] = {}
    for i, cells in enumerate(body):
        if len(errors) >= MAX_ERRORS:
            break
        line = i + 2
        if len(cells) != len(header):
            continue  # already reported as row_width
        row = dict(zip(header, cells, strict=False))
        row_dicts.append(row)
        for col, value in row.items():
            _check_cell(col, value, table, errors, line)
        pk = tuple((row.get(col) or "").strip() for col in table.primary_key)
        if all(pk):
            if pk in pk_seen:
                _err(
                    errors,
                    line,
                    "pk_duplicate",
                    f"duplicate primary key {pk} (first seen at line {pk_seen[pk]})",
                )
            else:
                pk_seen[pk] = line

    return table, row_dicts, errors


def _require_tenant(tenant_id: str | None) -> str:
    if tenant_id is None or not tenant_id.strip():
        raise TenantScopeMissing("tenant_id must be a non-empty string")
    return tenant_id.strip()


def _profile_for_client(client_id: str | None) -> str | None:
    profile = (client_id or "").strip().casefold()
    return profile if profile in {"callcenterclient", "sportacademyclient"} else None


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _record_batch(
    conn: sqlite3.Connection,
    *,
    batch_id: str,
    tenant_id: str,
    client_id: str | None,
    domain_id: str | None,
    filename: str,
    table_name: str,
    status: str,
    rows_total: int,
    rows_loaded: int,
    rows_rejected: int,
    errors: list[dict[str, Any]],
    created_by: str,
) -> None:
    conn.execute(
        """INSERT INTO import_batches (
               batch_id, tenant_id, client_id, domain_id, filename, table_name, status,
               rows_total, rows_loaded, rows_rejected, errors_json,
               provenance_data_mode, created_by, created_at
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'simulated_realistic', ?, ?)""",
        (
            batch_id,
            tenant_id,
            client_id,
            domain_id,
            filename,
            table_name,
            status,
            rows_total,
            rows_loaded,
            rows_rejected,
            json.dumps(errors),
            created_by,
            _now(),
        ),
    )


def _audit_node(
    conn: sqlite3.Connection,
    *,
    tenant_id: str,
    client_id: str | None,
    domain_id: str | None,
    batch_id: str,
    actor_id: str,
    filename: str,
    table_name: str | None,
    status: str,
    rows_loaded: int,
) -> None:
    from helix_codex_app import db

    db.record_node(
        conn,
        tenant_id=tenant_id,
        client_id=client_id,
        domain_id=domain_id,
        correlation_id=batch_id,
        classification="internal",
        nature="historical_event",
        created_by=actor_id,
        provenance_source="helix_codex_app.imports",
        provenance_data_mode="simulated_realistic",
        kind="import_batch",
        body={
            "filename": filename,
            "table_name": table_name,
            "batch_id": batch_id,
            "status": status,
            "rows_loaded": rows_loaded,
        },
    )


def import_bytes(
    conn: sqlite3.Connection,
    *,
    tenant_id: str,
    client_id: str | None,
    domain_id: str | None,
    filename: str,
    raw: bytes,
    actor_id: str,
    commit: bool,
) -> ImportReport:
    """Validate (and optionally commit) one uploaded CSV for one tenant."""
    tenant_id = _require_tenant(tenant_id)
    if not actor_id.strip():
        raise ValueError("actor_id must be a non-empty string")
    filename = pathlib.PurePath(filename.replace("\\", "/")).name
    if not filename:
        filename = "upload.csv"
    if len(raw) > schemas.MAX_BYTES:
        return ImportReport(
            ok=False,
            errors=[
                {
                    "line": None,
                    "code": "too_large",
                    "message": f"file exceeds {schemas.MAX_BYTES // (1024 * 1024)} MB",
                }
            ],
        )
    table, row_dicts, errors = validate(raw)
    expected_profile = _profile_for_client(client_id)
    if table is not None:
        if expected_profile is None:
            _err(
                errors,
                1,
                "tenant_profile",
                "client_id must identify callcenterclient or sportacademyclient",
            )
        elif table.tenant_profile != expected_profile:
            _err(
                errors,
                1,
                "tenant_profile",
                f"file belongs to {table.tenant_profile}, not {expected_profile}",
            )
    rows_total = len(row_dicts)
    batch_id = f"import-{uuid.uuid4().hex}"

    if table is None or errors:
        if commit:
            try:
                conn.execute("BEGIN")
                _record_batch(
                    conn,
                    batch_id=batch_id,
                    tenant_id=tenant_id,
                    client_id=client_id,
                    domain_id=domain_id,
                    filename=filename,
                    table_name=table.table_name if table else "unknown",
                    status="quarantined",
                    rows_total=rows_total,
                    rows_loaded=0,
                    rows_rejected=max(rows_total, 1),
                    errors=errors,
                    created_by=actor_id,
                )
                _audit_node(
                    conn,
                    tenant_id=tenant_id,
                    client_id=client_id,
                    domain_id=domain_id,
                    batch_id=batch_id,
                    actor_id=actor_id,
                    filename=filename,
                    table_name=table.table_name if table else None,
                    status="quarantined",
                    rows_loaded=0,
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return ImportReport(
            ok=False,
            table_name=table.table_name if table else None,
            tenant_profile=table.tenant_profile if table else None,
            rows_total=rows_total,
            rows_loaded=0,
            errors=errors,
            batch_id=batch_id if commit else None,
        )

    if not commit:
        return ImportReport(
            ok=True,
            table_name=table.table_name,
            tenant_profile=table.tenant_profile,
            rows_total=rows_total,
            rows_loaded=rows_total,
            errors=[],
        )

    now = _now()
    try:
        conn.execute("BEGIN")
        _record_batch(
            conn,
            batch_id=batch_id,
            tenant_id=tenant_id,
            client_id=client_id,
            domain_id=domain_id,
            filename=filename,
            table_name=table.table_name,
            status="loaded",
            rows_total=rows_total,
            rows_loaded=rows_total,
            rows_rejected=0,
            errors=[],
            created_by=actor_id,
        )
        for row in row_dicts:
            row_pk = "|".join((row.get(col) or "").strip() for col in table.primary_key)
            conn.execute(
                """INSERT INTO imported_rows (import_id, batch_id, tenant_id, table_name, row_pk, row_json, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(tenant_id, table_name, row_pk)
                   DO UPDATE SET row_json = excluded.row_json,
                                 batch_id = excluded.batch_id,
                                 created_at = excluded.created_at""",
                (
                    f"row-{uuid.uuid4().hex}",
                    batch_id,
                    tenant_id,
                    table.table_name,
                    row_pk,
                    json.dumps(row, default=str),
                    now,
                ),
            )
        _audit_node(
            conn,
            tenant_id=tenant_id,
            client_id=client_id,
            domain_id=domain_id,
            batch_id=batch_id,
            actor_id=actor_id,
            filename=filename,
            table_name=table.table_name,
            status="loaded",
            rows_loaded=rows_total,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return ImportReport(
        ok=True,
        table_name=table.table_name,
        tenant_profile=table.tenant_profile,
        rows_total=rows_total,
        rows_loaded=rows_total,
        errors=[],
        batch_id=batch_id,
    )


def list_batches(conn: sqlite3.Connection, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
    tenant_id = _require_tenant(tenant_id)
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    rows = conn.execute(
        """SELECT batch_id, tenant_id, filename, table_name, status, rows_total,
                  rows_loaded, rows_rejected, provenance_data_mode, created_at
             FROM import_batches
            WHERE tenant_id = ?
            ORDER BY created_at DESC
            LIMIT ?""",
        (tenant_id, limit),
    ).fetchall()
    cols = [
        "batch_id",
        "tenant_id",
        "filename",
        "table_name",
        "status",
        "rows_total",
        "rows_loaded",
        "rows_rejected",
        "provenance_data_mode",
        "created_at",
    ]
    return [dict(zip(cols, row, strict=True)) for row in rows]


def get_batch(conn: sqlite3.Connection, tenant_id: str, batch_id: str) -> dict[str, Any] | None:
    tenant_id = _require_tenant(tenant_id)
    row = conn.execute(
        """SELECT batch_id, tenant_id, filename, table_name, status, rows_total,
                  rows_loaded, rows_rejected, errors_json, provenance_data_mode,
                  created_by, created_at
             FROM import_batches
            WHERE batch_id = ? AND tenant_id = ?""",
        (batch_id, tenant_id),
    ).fetchone()
    if row is None:
        return None
    cols = [
        "batch_id",
        "tenant_id",
        "filename",
        "table_name",
        "status",
        "rows_total",
        "rows_loaded",
        "rows_rejected",
        "errors_json",
        "provenance_data_mode",
        "created_by",
        "created_at",
    ]
    out = dict(zip(cols, row, strict=True))
    out["errors"] = json.loads(out.pop("errors_json") or "[]")
    return out


def discard_batch(
    conn: sqlite3.Connection,
    *,
    tenant_id: str,
    batch_id: str,
    actor_id: str,
) -> bool:
    tenant_id = _require_tenant(tenant_id)
    if not actor_id.strip():
        raise ValueError("actor_id must be a non-empty string")
    try:
        conn.execute("BEGIN")
        batch = conn.execute(
            """SELECT filename, table_name, client_id, domain_id
                 FROM import_batches
                WHERE batch_id = ? AND tenant_id = ?""",
            (batch_id, tenant_id),
        ).fetchone()
        if batch is None:
            conn.rollback()
            return False
        conn.execute(
            "DELETE FROM imported_rows WHERE batch_id = ? AND tenant_id = ?",
            (batch_id, tenant_id),
        )
        conn.execute(
            "UPDATE import_batches SET status = 'discarded' WHERE batch_id = ? AND tenant_id = ?",
            (batch_id, tenant_id),
        )
        _audit_node(
            conn,
            tenant_id=tenant_id,
            client_id=batch["client_id"],
            domain_id=batch["domain_id"],
            batch_id=batch_id,
            actor_id=actor_id,
            filename=batch["filename"],
            table_name=batch["table_name"],
            status="discarded",
            rows_loaded=0,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return True
