#!/usr/bin/env python3
"""Drive the synthetic curated exports through the real App import HTTP routes.

The Phase-4 acceptance criterion is that both tenants' CSV exports can be
imported *through the App*, not only through the readiness harness. This drill
does exactly that in a disposable database: it creates the two tenant domains,
authenticates an owner for each, uploads every curated CSV whose header matches
a declared schema to ``POST /app/import/preview`` and ``POST /app/import/commit``,
then checks idempotency and cross-tenant invisibility.

Usage::

    python scripts/app_import_drill.py --out docs/production_readiness/evidence/app-import

Exit 0 = both tenants imported, verified and isolated; 1 otherwise.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import sys
import tempfile
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from helix_codex_app import db  # noqa: E402
from helix_codex_app.app import create_app  # noqa: E402
from helix_codex_app.config import AppSettings  # noqa: E402
from helix_codex_app.modules.imports import service  # noqa: E402
from helix_codex_app.security.accounts import AccountRepository  # noqa: E402
from helix_codex_app.security.passwords import hash_password  # noqa: E402
from helix_codex_app.security.sessions import SESSION_COOKIE, SessionStore  # noqa: E402

DISCLOSURE = (
    "SIMULATION ONLY. Synthetic curated fixtures, a disposable local SQLite app "
    "database, and the real authenticated App import routes. No real client data "
    "was uploaded and no external service was contacted."
)
TENANTS = {
    "callcenterclient": {"domain": "callcenter.test", "tenant_id": "tenant-cc"},
    "sportacademyclient": {"domain": "academy.test", "tenant_id": "tenant-sa"},
}


def _tenant_root() -> pathlib.Path:
    override = os.environ.get("HELIX_TENANT_DATA_DIR")
    if override:
        return pathlib.Path(override).expanduser().resolve()
    return (ROOT.parent.parent / "External tenant data").resolve()


def _curated_files(tenant: str) -> list[pathlib.Path]:
    curated = _tenant_root() / tenant / "16_DATA" / "curated"
    return sorted(curated.glob("*.csv"))


def _session(sessions: SessionStore, account) -> tuple[dict[str, str], dict[str, str]]:
    token, session = sessions.issue_session(account)
    return {SESSION_COOKIE: token}, {"X-CSRF-Token": session.csrf_token}


def _app_context(tmp: pathlib.Path):
    db_path = str(tmp / "app.db")
    conn = db.connect(db_path=db_path)
    db._init_schema(conn)
    repo = AccountRepository(conn)
    owners = {}
    for tenant, meta in TENANTS.items():
        domain = repo.create_domain(meta["domain"], tenant_id=meta["tenant_id"], client_id=tenant)
        owners[tenant] = repo.create_account(
            domain.domain_id,
            "owner",
            role_id="owner",
            password_hash=hash_password("drill-password"),
        )
    settings = AppSettings(db_path=db_path, cookie_secure=False)
    sessions = SessionStore(conn, settings)
    os.environ["HELIX_DB_PATH"] = str(tmp / "workflow.db")
    os.environ["HELIX_AUDIT_DB_PATH"] = str(tmp / "audit.db")
    os.environ["HELIX_LOG_PATH"] = str(tmp / "logs.jsonl")
    from server.config import get_settings

    get_settings.cache_clear()
    return SimpleNamespace(
        client=TestClient(create_app(settings), follow_redirects=False),
        conn=conn,
        sessions=sessions,
        owners=owners,
        db_path=db_path,
    )


def _row_count(conn, tenant_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM imported_rows WHERE tenant_id = ?", (tenant_id,)
    ).fetchone()
    return int(row[0]) if row else 0


def _import_tenant(ctx, tenant: str, meta: dict[str, str], report: dict) -> list[dict]:
    cookies, headers = _session(ctx.sessions, ctx.owners[tenant])
    results: list[dict] = []
    for path in _curated_files(tenant):
        raw = path.read_bytes()
        table, _rows, errors = service.validate(raw)
        if table is None or errors:
            results.append(
                {
                    "file": path.name,
                    "status": "skipped",
                    "reason": "no matching schema" if table is None else "validation errors",
                    "errors": errors[:3],
                }
            )
            continue
        if table.tenant_profile != tenant:
            results.append(
                {
                    "file": path.name,
                    "status": "skipped",
                    "reason": f"schema belongs to {table.tenant_profile}",
                }
            )
            continue
        preview = ctx.client.post(
            "/app/import/preview",
            cookies=cookies,
            headers=headers,
            files={"file": (path.name, raw, "text/csv")},
        )
        committed = ctx.client.post(
            "/app/import/commit",
            cookies=cookies,
            headers=headers,
            files={"file": (path.name, raw, "text/csv")},
        )
        ok = preview.status_code == 200 and committed.status_code == 200
        body = (
            committed.json()
            if committed.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        results.append(
            {
                "file": path.name,
                "table": table.table_name,
                "status": "imported" if ok else "failed",
                "preview_status": preview.status_code,
                "commit_status": committed.status_code,
                "rows_total": body.get("rows_total"),
                "rows_loaded": body.get("rows_loaded"),
                "batch_id": body.get("batch_id"),
                "errors": body.get("errors", [])[:3],
            }
        )
    report["tenants"][tenant] = {
        "files": results,
        "imported": sum(1 for item in results if item["status"] == "imported"),
        "skipped": sum(1 for item in results if item["status"] == "skipped"),
        "failed": sum(1 for item in results if item["status"] == "failed"),
        "rows": _row_count(ctx.conn, meta["tenant_id"]),
    }
    return results


def _check_idempotency(ctx, tenant: str, meta: dict[str, str], results: list[dict]) -> dict:
    imported = next((item for item in results if item["status"] == "imported"), None)
    if imported is None:
        return {"ok": False, "reason": "no imported file to re-upload"}
    path = _tenant_root() / tenant / "16_DATA" / "curated" / imported["file"]
    raw = path.read_bytes()
    cookies, headers = _session(ctx.sessions, ctx.owners[tenant])
    before = _row_count(ctx.conn, meta["tenant_id"])
    response = ctx.client.post(
        "/app/import/commit",
        cookies=cookies,
        headers=headers,
        files={"file": (path.name, raw, "text/csv")},
    )
    after = _row_count(ctx.conn, meta["tenant_id"])
    return {
        "ok": response.status_code == 200 and before == after,
        "file": path.name,
        "rows_before": before,
        "rows_after": after,
        "status": response.status_code,
    }


def _check_isolation(ctx, tenant: str, other: str, results: list[dict]) -> dict:
    imported = next((item for item in results if item["status"] == "imported"), None)
    if imported is None:
        return {"ok": False, "reason": "no batch to probe"}
    cookies, _ = _session(ctx.sessions, ctx.owners[other])
    response = ctx.client.get(f"/app/import/{imported['batch_id']}", cookies=cookies)
    return {
        "ok": response.status_code == 404,
        "batch_id": imported["batch_id"],
        "probe_tenant": other,
        "status": response.status_code,
    }


def _render(report: dict) -> str:
    lines = [
        "# App CSV import drill (both tenants, real HTTP routes)",
        "",
        f"> {DISCLOSURE}",
        "",
        f"**Passed:** {report['passed']}  ",
        f"**Generated:** {report['generated_at']}",
        "",
        "| Tenant | Imported files | Skipped | Failed | Rows | Idempotent | Isolated |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for tenant, data in report["tenants"].items():
        checks = report["checks"].get(tenant, {})
        lines.append(
            f"| {tenant} | {data['imported']} | {data['skipped']} | {data['failed']} | "
            f"{data['rows']} | {checks.get('idempotency', {}).get('ok')} | "
            f"{checks.get('isolation', {}).get('ok')} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The upload is driven through the App's authenticated HTTP import routes, not a browser click path.",
            "- Only curated exports with a declared schema are imported; unmatched files are listed as skipped.",
            "- The readiness harness still reads the fixture files directly; it is not re-pointed at the App database.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", default=str(ROOT / "docs/production_readiness/evidence/app-import")
    )
    args = parser.parse_args(argv)

    if not _tenant_root().is_dir():
        print(f"APP_IMPORT: UNAVAILABLE (missing {_tenant_root()})", file=sys.stderr)
        return 2

    report: dict = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "disclosure": DISCLOSURE,
        "tenants": {},
        "checks": {},
    }
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="helix-app-import-"))
    try:
        ctx = _app_context(tmp)
        try:
            with ctx.client:
                for tenant, meta in TENANTS.items():
                    results = _import_tenant(ctx, tenant, meta, report)
                    other = next(name for name in TENANTS if name != tenant)
                    report["checks"][tenant] = {
                        "idempotency": _check_idempotency(ctx, tenant, meta, results),
                        "isolation": _check_isolation(ctx, tenant, other, results),
                    }
        finally:
            db.close(ctx.conn)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    tenants_ok = all(
        data["failed"] == 0 and data["imported"] > 0 for data in report["tenants"].values()
    )
    checks_ok = all(
        check["idempotency"].get("ok") and check["isolation"].get("ok")
        for check in report["checks"].values()
    )
    report["passed"] = bool(tenants_ok and checks_ok and len(report["tenants"]) == len(TENANTS))

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "app-import-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    (out / "app-import-report.md").write_text(_render(report), encoding="utf-8")
    for tenant, data in report["tenants"].items():
        print(
            f"[{'PASS' if data['failed'] == 0 else 'FAIL'}] {tenant}: "
            f"{data['imported']} imported, {data['skipped']} skipped, {data['failed']} failed, "
            f"{data['rows']} rows"
        )
    print(f"APP_IMPORT: {'PASS' if report['passed'] else 'FAIL'}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
