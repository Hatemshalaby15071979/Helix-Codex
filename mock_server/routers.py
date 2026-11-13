"""
Route handlers for the mock server.

These mirror the JSON contract of the real Helix-Codex API surface:

  server/app.py         -> /healthz /readyz /api/workflows /api/approvals
                           /api/halt/* /api/chat/* /api/tasks/* /api/docs/*
                           /api/stream/* /metrics
  helix_codex_app/app.py -> /app/healthz /app/api/tasks /app/api/documents
                           /app/api/events /app/api/oncall* /app/api/attendance/*
                           /app/api/ops/* /app/api/conversations* /app/api/notifications*
                           /app/api/memory/* /app/api/sections /app/api/packs

HTML/HTMX screen routes are intentionally NOT mocked — a frontend dev targets
the JSON endpoints, and the shell's own server-rendered pages need the real app.
SSE endpoints return a single keep-alive frame then close, so the browser's
EventSource can attach without the test client hanging.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from .state import MockState, _id, _now


def _ok(body: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(body, status_code=status)


def register_routes(
    app: Any, state: MockState, scenario: Callable[[], Any]
) -> None:
    """Attach every mock route to the FastAPI app."""

    # -- control --------------------------------------------------------------
    @app.get("/__mock/state")
    def dump_state() -> JSONResponse:
        return _ok(
            {
                "workflows": len(state.workflows),
                "tasks": len(state.tasks),
                "documents": len(state.documents),
                "conversations": len(state.conversations),
                "notifications": len(state.notifications),
                "request_log": state.request_log[-20:],
            }
        )

    @app.post("/__mock/reset")
    def reset_state() -> JSONResponse:
        state.reset()
        return _ok({"reset": True})

    # -- health (server) ------------------------------------------------------
    @app.get("/healthz")
    def healthz() -> JSONResponse:
        return _ok({"status": "ok", "profile": "mock", "version": "0.9.0"})

    @app.get("/readyz")
    def readyz(response: Response) -> JSONResponse:
        return _ok({"ready": True, "checks": {"workflow_store": True, "audit_chain": True}})

    @app.get("/app/healthz")
    def app_healthz() -> JSONResponse:
        return _ok({"status": "ok", "app": "helix-codex"})

    # -- workflows (server) ---------------------------------------------------
    @app.post("/api/workflows")
    async def submit_workflow(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        wf_id = _id("wf")
        wf = {
            "workflow_id": wf_id,
            "task_id": _id("task"),
            "state": "awaiting_approval" if body.get("requires_approval") else "accepted",
            "capability": body.get("capability", "unknown"),
            "tenant_id": body.get("tenant_id", "tenant_demo"),
            "client_id": body.get("client_id", "client_demo"),
            "correlation_id": _id("corr"),
            "error": None,
            "result": None,
            "approval": None,
        }
        state.workflows[wf_id] = wf
        if not scenario().stateful:
            return _ok(wf, 202)
        if wf["state"] == "awaiting_approval":
            state.approvals[wf_id] = wf
            return _ok(wf, 409)
        return _ok(wf, 202)

    @app.get("/api/workflows")
    def list_workflows() -> JSONResponse:
        return _ok(list(state.workflows.values()))

    @app.get("/api/workflows/{workflow_id}")
    def get_workflow(workflow_id: str) -> JSONResponse:
        wf = state.workflows.get(workflow_id)
        if wf is None:
            return _ok({"error": f"workflow {workflow_id!r} not found"}, 404)
        return _ok(wf)

    @app.get("/api/workflows/{workflow_id}/events")
    def workflow_events(workflow_id: str) -> JSONResponse:
        return _ok(
            [{"event": "submitted", "at": _now(), "workflow_id": workflow_id}]
        )

    @app.post("/api/workflows/{workflow_id}/execute")
    def execute_workflow(workflow_id: str) -> JSONResponse:
        wf = state.workflows.get(workflow_id)
        if wf is None:
            return _ok({"error": f"workflow {workflow_id!r} not found"}, 404)
        wf["state"] = "completed"
        wf["result"] = {"ok": True}
        return _ok(wf)

    @app.get("/api/workflows/{workflow_id}/result")
    def workflow_result(workflow_id: str) -> JSONResponse:
        wf = state.workflows.get(workflow_id)
        if wf is None:
            return _ok({"error": f"workflow {workflow_id!r} not found"}, 404)
        return _ok({"result": wf.get("result") or {}, "state": wf["state"]})

    # -- approvals (server) ---------------------------------------------------
    @app.get("/api/approvals")
    def list_approvals() -> JSONResponse:
        return _ok(list(state.approvals.values()))

    @app.post("/api/approvals/{workflow_id}")
    async def decide_approval(workflow_id: str, request: Request) -> JSONResponse:
        wf = state.workflows.get(workflow_id)
        if wf is None:
            return _ok({"error": f"workflow {workflow_id!r} not found"}, 404)
        body = await _json_body_async(request)
        decision = body.get("decision", "approved")
        wf["state"] = "completed" if decision == "approved" else "rejected"
        wf["approval"] = {
            "decision": decision,
            "reason": body.get("reason", ""),
            "at": _now(),
        }
        state.approvals.pop(workflow_id, None)
        return _ok(wf)

    # -- halt (server) --------------------------------------------------------
    @app.get("/api/halt/status")
    def halt_status() -> JSONResponse:
        return _ok(state.halt)

    @app.post("/api/halt/engage")
    async def halt_engage(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        state.halt = {
            "engaged": True,
            "scope": "global" if body.get("tenant_id") is None else "tenant",
            "reason": body.get("reason"),
            "actor": "mock_actor",
            "engaged_at": _now(),
            "tenants": [body["tenant_id"]] if body.get("tenant_id") else [],
        }
        return _ok(state.halt)

    @app.post("/api/halt/release")
    def halt_release() -> JSONResponse:
        state.halt = {
            "engaged": False,
            "scope": "none",
            "reason": None,
            "actor": None,
            "engaged_at": None,
            "tenants": [],
        }
        return _ok(state.halt)

    # -- chat (server) -------------------------------------------------------
    @app.post("/api/chat/messages")
    async def create_chat_message(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        msg = {
            "node_id": _id("msg"),
            "tenant_id": "default",
            "client_id": None,
            "correlation_id": "chat_default",
            "causation_id": None,
            "classification": "internal",
            "nature": "user_claim",
            "created_by": "user",
            "created_at": _now(),
            "kind": "message",
            "body": {"content": body.get("message", "")},
        }
        state.chat_messages.append(msg)
        return _ok({"status": "ok", "node_id": msg["node_id"]})

    @app.get("/api/chat/messages")
    def list_chat_messages() -> JSONResponse:
        return _ok([m for m in state.chat_messages])

    # -- tasks (server) ------------------------------------------------------
    @app.post("/api/tasks/")
    async def create_server_task(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        node = {
            "node_id": _id("task"),
            "tenant_id": "default",
            "kind": "task",
            "body": {
                "title": body.get("title", ""),
                "description": body.get("description", ""),
                "assignee": body.get("assignee"),
                "status": "open",
            },
            "created_at": _now(),
        }
        state.server_tasks.append(node)
        return _ok({"status": "ok", "node_id": node["node_id"]})

    @app.get("/api/tasks/")
    def list_server_tasks() -> JSONResponse:
        return _ok([t for t in state.server_tasks])

    @app.put("/api/tasks/{task_id}/status")
    async def update_server_task_status(task_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        for t in state.server_tasks:
            if t["node_id"] == task_id:
                t["body"]["status"] = body.get("status", "open")
                return _ok({"status": "ok"})
        return _ok({"status": "ok"})

    # -- docs (server) -------------------------------------------------------
    @app.post("/api/docs/")
    async def create_server_doc(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        node = {
            "node_id": _id("doc"),
            "tenant_id": "default",
            "kind": "document",
            "body": {"title": body.get("title", ""), "content": body.get("content", "")},
            "created_at": _now(),
        }
        state.server_docs.append(node)
        return _ok({"status": "ok", "node_id": node["node_id"]})

    @app.get("/api/docs/")
    def list_server_docs() -> JSONResponse:
        return _ok([d for d in state.server_docs])

    @app.get("/api/docs/{doc_id}")
    def get_server_doc(doc_id: str) -> JSONResponse:
        for d in state.server_docs:
            if d["node_id"] == doc_id:
                return _ok(d)
        return _ok({"error": "Document not found"}, 404)

    # -- stream (server) -----------------------------------------------------
    @app.get("/api/stream/{correlation_id}")
    async def stream_workflow(request: Request, correlation_id: str) -> StreamingResponse:
        async def gen():
            yield ": keep-alive\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.get("/api/stream/{correlation_id}/workflow")
    def stream_workflow_lookup(correlation_id: str) -> JSONResponse:
        for wf in state.workflows.values():
            if wf["correlation_id"] == correlation_id:
                return _ok(wf)
        return _ok({"error": f"no workflow for correlation {correlation_id!r}"}, 404)

    # -- metrics (server) ----------------------------------------------------
    @app.get("/metrics")
    def metrics() -> Response:
        text = (
            "# HELP helix_http_requests_total Total HTTP requests.\n"
            "# TYPE helix_http_requests_total counter\n"
            "helix_http_requests_total 1\n"
        )
        return Response(content=text, media_type="text/plain; version=0.0.4")

    # == helix_codex_app JSON surface ========================================

    # -- tasks ---------------------------------------------------------------
    @app.get("/app/api/tasks")
    def list_app_tasks() -> JSONResponse:
        return _ok([t for t in state.tasks.values()])

    @app.post("/app/api/tasks")
    async def create_app_task(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        tid = _id("task")
        task = {
            "task_id": tid,
            "title": body.get("title", "Untitled"),
            "description": body.get("description", ""),
            "priority": body.get("priority", "medium"),
            "status": "open",
            "assignee_account_id": body.get("assignee_account_id"),
            "created_at": _now(),
            "comments": [],
        }
        state.tasks[tid] = task
        return _ok(task, 201)

    @app.get("/app/api/tasks/{task_id}")
    def get_app_task(task_id: str) -> JSONResponse:
        task = state.tasks.get(task_id)
        if task is None:
            return _ok({"error": "task not found"}, 404)
        return _ok({"task": task, "comments": task.get("comments", [])})

    @app.put("/app/api/tasks/{task_id}")
    async def update_app_task(task_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        task = state.tasks.get(task_id)
        if task is None:
            return _ok({"error": "task not found"}, 404)
        for key in ("title", "description", "priority"):
            if key in body:
                task[key] = body[key]
        return _ok(task)

    @app.post("/app/api/tasks/{task_id}/status")
    async def set_app_task_status(task_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        task = state.tasks.get(task_id)
        if task is None:
            return _ok({"error": "task not found"}, 404)
        task["status"] = body.get("status", task["status"])
        return _ok(task)

    @app.post("/app/api/tasks/{task_id}/comments")
    async def add_app_task_comment(task_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        task = state.tasks.get(task_id)
        if task is None:
            return _ok({"error": "task not found"}, 404)
        comment = {
            "comment_id": _id("cmt"),
            "task_id": task_id,
            "account_id": "account_demo",
            "body": body.get("body", ""),
            "created_at": _now(),
        }
        task.setdefault("comments", []).append(comment)
        return _ok(comment, 201)

    # -- documents -----------------------------------------------------------
    @app.get("/app/api/documents")
    def list_app_documents() -> JSONResponse:
        return _ok([d for d in state.documents.values()])

    @app.post("/app/api/documents")
    async def create_app_document(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        did = _id("doc")
        doc = {
            "document_id": did,
            "title": body.get("title", "Untitled"),
            "doc_type": body.get("doc_type", "note"),
            "blocks": [],
            "versions": [{"version_no": 1, "created_at": _now()}],
        }
        state.documents[did] = doc
        return _ok(doc, 201)

    @app.get("/app/api/documents/{document_id}")
    def get_app_document(document_id: str) -> JSONResponse:
        doc = state.documents.get(document_id)
        if doc is None:
            return _ok({"error": "document not found"}, 404)
        return _ok({"document": doc, "blocks": doc.get("blocks", [])})

    @app.post("/app/api/documents/{document_id}/blocks")
    async def insert_app_block(document_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        doc = state.documents.get(document_id)
        if doc is None:
            return _ok({"error": "document not found"}, 404)
        block = {"block_id": _id("blk"), "content": body.get("content", "")}
        doc.setdefault("blocks", []).append(block)
        return _ok(block, 201)

    @app.put("/app/api/documents/{document_id}/blocks/{block_id}")
    async def update_app_block(document_id: str, block_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        doc = state.documents.get(document_id)
        if doc is None:
            return _ok({"error": "document not found"}, 404)
        for b in doc.get("blocks", []):
            if b["block_id"] == block_id:
                b["content"] = body.get("content", b["content"])
                return _ok(b)
        return _ok({"error": "block not found"}, 404)

    # -- calendar / events ---------------------------------------------------
    @app.get("/app/api/events")
    def list_events() -> JSONResponse:
        return _ok({"events": state.events, "from": _now(), "to": _now()})

    @app.post("/app/api/events")
    async def create_event(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        eid = _id("evt")
        event = {
            "event_id": eid,
            "title": body.get("title", "Event"),
            "kind": body.get("kind", "event"),
            "starts_at": body.get("starts_at", _now()),
            "ends_at": body.get("ends_at", _now()),
            "all_day": bool(body.get("all_day", False)),
            "location": body.get("location"),
            "room_id": body.get("room_id"),
            "status": "scheduled",
            "creator_account_id": "account_demo",
            "attendees": [
                {
                    "account_id": "account_demo",
                    "response": "accepted",
                    "display_name": "Demo User",
                }
            ],
        }
        state.events.append(event)
        return _ok(event, 201)

    @app.put("/app/api/events/{event_id}")
    async def update_event(event_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        for e in state.events:
            if e["event_id"] == event_id:
                if body.get("status") == "cancelled":
                    e["status"] = "cancelled"
                else:
                    for key in ("title", "kind", "starts_at", "ends_at", "location"):
                        if key in body:
                            e[key] = body[key]
                return _ok(e)
        return _ok({"error": "event not found"}, 404)

    @app.post("/app/api/events/{event_id}/respond")
    async def respond_event(event_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        for e in state.events:
            if e["event_id"] == event_id:
                for att in e["attendees"]:
                    if att["account_id"] == "account_demo":
                        att["response"] = body.get("response", "accepted")
                return _ok(e)
        return _ok({"error": "event not found"}, 404)

    @app.get("/app/api/oncall")
    def oncall() -> JSONResponse:
        return _ok(
            {
                "coverage": {"primary": "account_demo", "backup": None},
                "next_shifts": [],
                "wfm": {"staffing": "adequate"},
            }
        )

    @app.post("/app/api/oncall/shifts")
    async def create_shift(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        shift = {
            "shift_id": _id("shift"),
            "starts_at": body.get("starts_at", _now()),
            "ends_at": body.get("ends_at", _now()),
            "primary_account_id": body.get("primary_account_id"),
            "backup_account_id": body.get("backup_account_id"),
        }
        return _ok(shift, 201)

    # -- attendance ----------------------------------------------------------
    @app.post("/app/api/attendance/punch")
    async def punch(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        action = body.get("action")
        if action not in ("in", "out"):
            action = "out" if state.attendance["open"] else "in"
        if action == "in":
            state.attendance = {
                "open": True,
                "action": "out",
                "punched_at": _now(),
            }
            return _ok({"punched_at": state.attendance["punched_at"], "action": "in"}, 201)
        state.attendance = {"open": False, "action": "in", "punched_at": _now()}
        return _ok({"punched_at": state.attendance["punched_at"], "action": "out"}, 201)

    @app.get("/app/api/attendance/records")
    def attendance_records() -> JSONResponse:
        return _ok({"records": [], "from": _now(), "to": _now()})

    @app.get("/app/api/attendance/summary")
    def attendance_summary() -> JSONResponse:
        return _ok({"by_day": {}, "total_minutes": 0})

    # -- ops ----------------------------------------------------------------
    @app.post("/app/api/ops/workflows")
    async def ops_submit(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        wf_id = _id("wf")
        card = {
            "workflow_id": wf_id,
            "capability": body.get("capability", "unknown"),
            "state": "awaiting_approval" if body.get("requires_approval", True) else "accepted",
            "tenant_id": "tenant_demo",
            "created_at": _now(),
        }
        state.workflows[wf_id] = card
        return _ok(card, 201)

    @app.get("/app/api/ops/workflows/{workflow_id}")
    def ops_detail(workflow_id: str) -> JSONResponse:
        wf = state.workflows.get(workflow_id)
        if wf is None:
            return _ok({"error": f"workflow {workflow_id!r} not found"}, 404)
        return _ok(wf)

    @app.post("/app/api/ops/workflows/{workflow_id}/approve")
    async def ops_approve(workflow_id: str, request: Request) -> JSONResponse:
        wf = state.workflows.get(workflow_id)
        if wf is None:
            return _ok({"error": f"workflow {workflow_id!r} not found"}, 404)
        wf["state"] = "approved"
        return _ok(wf)

    @app.post("/app/api/ops/demo/wfm")
    async def wfm_demo(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        wf_id = _id("wf")
        report = {
            "workflow_id": wf_id,
            "capability": "wfm_forecast",
            "state": "completed",
            "result": {
                "service_level": 0.82,
                "agents_required": 7,
                "forecast": [12, 14, 11, 9],
            },
            "inputs": {
                "arrival_rate": body.get("arrival_rate", 14.2),
                "average_handling_time": body.get("average_handling_time", 6.0),
                "service_level_target": body.get("service_level_target", 0.8),
                "average_calls_per_period": body.get("average_calls_per_period", 200),
            },
        }
        return _ok(report, 201)

    @app.get("/app/api/ops/audit/{correlation_id}")
    def ops_audit(correlation_id: str) -> JSONResponse:
        return _ok(
            {
                "correlation_id": correlation_id,
                "events": [
                    {"event": "submitted", "at": _now()},
                    {"event": "approved", "at": _now()},
                ],
            }
        )

    # -- cockpit ------------------------------------------------------------
    @app.get("/app/api/cockpit/summary")
    def cockpit_summary() -> JSONResponse:
        return _ok(
            {
                "owner": "account_demo",
                "active_accounts": 1,
                "open_tasks": len(state.tasks),
                "approval_queue": len(state.approvals),
                "attendance_today_minutes": 0,
            }
        )

    # -- messaging ----------------------------------------------------------
    @app.get("/app/api/conversations")
    def list_conversations() -> JSONResponse:
        return _ok([c for c in state.conversations.values()])

    @app.post("/app/api/conversations")
    async def create_conversation(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        cid = _id("conv")
        conv = {
            "conversation_id": cid,
            "kind": "group" if body.get("member_ids") else "direct",
            "title": body.get("name"),
            "classification": "internal",
            "created_by": "account_demo",
            "created_at": _now(),
            "correlation_id": _id("corr"),
            "member_role": "member",
            "last_read_at": None,
            "message_count": 0,
            "last_message_at": None,
            "last_message_preview": None,
        }
        state.conversations[cid] = conv
        return _ok(conv, 201)

    @app.get("/app/api/conversations/{conversation_id}/messages")
    def list_messages(conversation_id: str) -> JSONResponse:
        msgs = [m for m in state.messages if m["conversation_id"] == conversation_id]
        return _ok({"messages": msgs, "next_before": None})

    @app.post("/app/api/conversations/{conversation_id}/messages")
    async def send_message(conversation_id: str, request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        msg = {
            "message_id": _id("msg"),
            "conversation_id": conversation_id,
            "sender_account_id": "account_demo",
            "body": body.get("body", ""),
            "classification": "internal",
            "created_at": _now(),
            "node_id": None,
        }
        state.messages.append(msg)
        return _ok(msg, 201)

    @app.post("/app/api/conversations/{conversation_id}/read")
    def mark_read(conversation_id: str) -> JSONResponse:
        return _ok({"ok": True})

    @app.get("/app/api/conversations/{conversation_id}/stream")
    async def conversation_stream(conversation_id: str) -> StreamingResponse:
        async def gen():
            yield ": keep-alive\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    # -- notifications ------------------------------------------------------
    @app.get("/app/api/notifications")
    def list_notifications() -> JSONResponse:
        return _ok(list(state.notifications.values()))

    @app.post("/app/api/notifications/read-all")
    def mark_all_read() -> JSONResponse:
        for n in state.notifications.values():
            n["read_at"] = _now()
        return _ok({"ok": True})

    @app.post("/app/api/notifications/{notification_id}/read")
    def mark_one_read(notification_id: str) -> JSONResponse:
        n = state.notifications.get(notification_id)
        if n is None:
            return _ok({"error": "no such notification"}, 404)
        n["read_at"] = _now()
        return _ok({"ok": True})

    @app.get("/app/api/notifications/stream")
    async def notification_stream() -> StreamingResponse:
        async def gen():
            yield "event: unread_count\ndata: {\"unread\": 0}\n\n"
        return StreamingResponse(gen(), media_type="text/event-stream")

    # -- memory -------------------------------------------------------------
    @app.get("/app/api/memory/proposals")
    def list_proposals() -> JSONResponse:
        return _ok({"proposals": [p for p in state.proposals.values()]})

    @app.get("/app/api/memory/proposals/{proposal_id}")
    def get_proposal(proposal_id: str) -> JSONResponse:
        p = state.proposals.get(proposal_id)
        if p is None:
            return _ok({"error": "proposal not found"}, 404)
        return _ok({"proposal": p, "reviews": []})

    @app.post("/app/api/memory/proposals")
    async def create_proposal(request: Request) -> JSONResponse:
        body = await _json_body_async(request)
        pid = _id("prop")
        proposal = {
            "proposal_id": pid,
            "kind": body.get("kind", "policy_change"),
            "target": body.get("target", ""),
            "state": "draft",
            "version": 1,
            "created_by": "account_demo",
            "created_at": _now(),
            "updated_at": _now(),
            "approval_state": "draft",
        }
        state.proposals[pid] = proposal
        return _ok({"proposal_id": pid, "state": "draft"}, 201)

    @app.post("/app/api/memory/proposals/{proposal_id}/evaluate")
    async def evaluate_proposal(proposal_id: str) -> JSONResponse:
        p = state.proposals.get(proposal_id)
        if p is None:
            return _ok({"error": "proposal not found"}, 404)
        p["approval_state"] = "evaluated"
        return _ok({"evaluation": {"score": 0.1, "baseline": 0.0, "proposed": 0.1}})

    @app.post("/app/api/memory/proposals/{proposal_id}/approve")
    async def approve_proposal(proposal_id: str) -> JSONResponse:
        p = state.proposals.get(proposal_id)
        if p is None:
            return _ok({"error": "proposal not found"}, 404)
        p["approval_state"] = "approved"
        return _ok({"proposal_id": proposal_id, "state": "approved"})

    @app.get("/app/api/memory/ledger/verify")
    def ledger_verify() -> JSONResponse:
        return _ok({"valid": True, "entries": len(state.proposals)})

    @app.get("/app/api/memory/promotions")
    def list_promotions() -> JSONResponse:
        return _ok({"promotions": []})

    # -- low-code -----------------------------------------------------------
    @app.get("/app/api/sections")
    def sections() -> JSONResponse:
        return _ok(
            {
                "sections": [
                    {"id": "tasks", "label": "Tasks", "permission": "tasks.use"},
                    {"id": "docs", "label": "Docs", "permission": "docs.read"},
                    {"id": "calendar", "label": "Calendar", "permission": "calendar.use"},
                ]
            }
        )

    @app.get("/app/api/packs")
    def packs() -> JSONResponse:
        return _ok({"packs": []})


# -- body parsing helpers ----------------------------------------------------
async def _json_body_async(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}
