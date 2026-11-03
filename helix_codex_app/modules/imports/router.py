"""Tenant-scoped upload routes for simulated curated CSV fixtures."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.datastructures import UploadFile

from helix_codex_app.db import close, connect
from helix_codex_app.modules.imports import schema, service
from helix_codex_app.security.accounts import Account
from helix_codex_app.security.guard import require_csrf, require_permission
from helix_codex_app.templating import render

imports_router = APIRouter(
    prefix="/app/import",
    dependencies=[Depends(require_permission("import.run"))],
)


@imports_router.get("", response_model=None)
def import_screen(request: Request) -> HTMLResponse:
    account = _account(request)
    conn = _conn(request)
    try:
        batches = service.list_batches(conn, account.tenant_id)
    finally:
        close(conn)
    return render(
        request,
        "imports/index.html",
        {"active_nav": "import", "account": account, "batches": batches},
    )


@imports_router.post("/preview", dependencies=[Depends(require_csrf)])
async def preview_import(request: Request) -> JSONResponse:
    return await _import_upload(request, commit=False)


@imports_router.post("/commit", dependencies=[Depends(require_csrf)])
async def commit_import(request: Request) -> JSONResponse:
    return await _import_upload(request, commit=True)


@imports_router.get("/{batch_id}")
def import_detail(request: Request, batch_id: str) -> JSONResponse:
    account = _account(request)
    conn = _conn(request)
    try:
        batch = service.get_batch(conn, account.tenant_id, batch_id)
    finally:
        close(conn)
    if batch is None:
        raise HTTPException(status_code=404, detail="import batch not found")
    return JSONResponse(batch)


@imports_router.post("/{batch_id}/discard", dependencies=[Depends(require_csrf)])
def discard_import(request: Request, batch_id: str) -> JSONResponse:
    account = _account(request)
    conn = _conn(request)
    try:
        discarded = service.discard_batch(
            conn,
            tenant_id=account.tenant_id,
            batch_id=batch_id,
            actor_id=account.account_id,
        )
    finally:
        close(conn)
    if not discarded:
        raise HTTPException(status_code=404, detail="import batch not found")
    return JSONResponse({"ok": True, "batch_id": batch_id, "status": "discarded"})


async def _import_upload(request: Request, *, commit: bool) -> JSONResponse:
    form = await request.form()
    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise HTTPException(status_code=422, detail="a CSV file is required")
    if not upload.filename or not upload.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="only .csv files are accepted")
    if upload.content_type not in {
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }:
        raise HTTPException(status_code=415, detail="upload must use a CSV content type")

    account = _account(request)
    raw = await upload.read(schema.MAX_BYTES + 1)
    conn = _conn(request)
    try:
        report = service.import_bytes(
            conn,
            tenant_id=account.tenant_id,
            client_id=account.client_id,
            domain_id=account.domain_id,
            filename=upload.filename,
            raw=raw,
            actor_id=account.account_id,
            commit=commit,
        )
    finally:
        close(conn)
    return JSONResponse(report.to_dict(), status_code=200 if report.ok else 422)


def _account(request: Request) -> Account:
    return request.state.account


def _conn(request: Request):
    return connect(db_path=request.app.state.settings.db_path)
