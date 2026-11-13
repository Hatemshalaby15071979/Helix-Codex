"""
In-memory state for the mock server.

Seeded from the real response shapes found in the project:
  - server/features/workflows/schemas.py  -> WorkflowResponse
  - server/features/health/schemas.py      -> HealthResponse / ReadinessResponse
  - server/models/node.py                   -> Node.to_dict() (chat/task/doc)
  - helix_codex_app/modules/messaging/schemas.py -> ConversationOut / MessageOut
  - helix_codex_app/modules/notifications/schemas.py -> NotificationOut

The mock never imports the governed engine, SQLite stores, or auth pipeline.
It keeps a simple dict-backed store so the frontend can exercise full CRUD
without a backend.
"""
from __future__ import annotations

import itertools
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

_counter = itertools.count(1)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MockState:
    """Mutable in-memory store that mimics the project's data shapes."""

    def __init__(self) -> None:
        self.workflows: dict[str, dict[str, Any]] = {}
        self.approvals: dict[str, dict[str, Any]] = {}
        self.chat_messages: list[dict[str, Any]] = []
        self.server_tasks: list[dict[str, Any]] = []
        self.server_docs: list[dict[str, Any]] = []
        self.halt: dict[str, Any] = {
            "engaged": False,
            "scope": "none",
            "reason": None,
            "actor": None,
            "engaged_at": None,
            "tenants": [],
        }
        # helix_codex_app surfaces
        self.tasks: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.conversations: dict[str, dict[str, Any]] = {}
        self.messages: list[dict[str, Any]] = []
        self.notifications: list[dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.attendance: dict[str, Any] = {"open": False, "action": "in", "punched_at": None}
        self.proposals: dict[str, dict[str, Any]] = {}
        self.request_log: list[dict[str, Any]] = []
        self._seed()

    # -- seeding -------------------------------------------------------------
    def _seed(self) -> None:
        self._seed_workflows()
        self._seed_chat()
        self._seed_app_tasks()
        self._seed_app_docs()
        self._seed_conversations()
        self._seed_notifications()
        self._seed_events()
        self._seed_proposals()

    def _seed_workflows(self) -> None:
        for i in range(3):
            wf_id = _id("wf")
            self.workflows[wf_id] = {
                "workflow_id": wf_id,
                "task_id": _id("task"),
                "state": "completed" if i < 2 else "awaiting_approval",
                "capability": "wfm_forecast",
                "tenant_id": "tenant_demo",
                "client_id": "client_demo",
                "correlation_id": _id("corr"),
                "error": None,
                "result": {"ok": True} if i < 2 else None,
                "approval": None,
            }
        for wf in self.workflows.values():
            if wf["state"] == "awaiting_approval":
                self.approvals[wf["workflow_id"]] = wf

    def _seed_chat(self) -> None:
        for i in range(3):
            self.chat_messages.append(
                {
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
                    "body": {"content": f"Mock chat message {i + 1}"},
                }
            )

    def _seed_app_tasks(self) -> None:
        for i, status in enumerate(("open", "doing", "done")):
            tid = _id("task")
            self.tasks[tid] = {
                "task_id": tid,
                "title": f"Sample task {i + 1}",
                "description": "Seeded by mock server",
                "priority": "medium",
                "status": status,
                "assignee_account_id": None,
                "created_at": _now(),
                "comments": [],
            }

    def _seed_app_docs(self) -> None:
        for i in range(2):
            did = _id("doc")
            self.documents[did] = {
                "document_id": did,
                "title": f"Sample document {i + 1}",
                "doc_type": "note",
                "blocks": [{"block_id": _id("blk"), "content": "First block"}],
                "versions": [{"version_no": 1, "created_at": _now()}],
            }

    def _seed_conversations(self) -> None:
        cid = _id("conv")
        self.conversations[cid] = {
            "conversation_id": cid,
            "kind": "direct",
            "title": None,
            "classification": "internal",
            "created_by": "account_demo",
            "created_at": _now(),
            "correlation_id": _id("corr"),
            "member_role": "member",
            "last_read_at": None,
            "message_count": 1,
            "last_message_at": _now(),
            "last_message_preview": "Hello from the mock",
        }
        self.messages.append(
            {
                "message_id": _id("msg"),
                "conversation_id": cid,
                "sender_account_id": "account_demo",
                "body": "Hello from the mock",
                "classification": "internal",
                "created_at": _now(),
                "node_id": None,
            }
        )

    def _seed_notifications(self) -> None:
        for i in range(2):
            nid = _id("notif")
            self.notifications[nid] = {
                "notification_id": nid,
                "account_id": "account_demo",
                "kind": "info",
                "title": f"Mock notification {i + 1}",
                "body": "Seeded by mock server",
                "link": None,
                "read_at": None,
                "created_at": _now(),
                "correlation_id": _id("corr"),
            }

    def _seed_events(self) -> None:
        start = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
        for i in range(2):
            eid = _id("evt")
            self.events.append(
                {
                    "event_id": eid,
                    "title": f"Standup {i + 1}",
                    "kind": "event",
                    "starts_at": (start + timedelta(days=i)).isoformat(),
                    "ends_at": (start + timedelta(days=i, hours=1)).isoformat(),
                    "all_day": False,
                    "location": "Room A",
                    "room_id": None,
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
            )

    def _seed_proposals(self) -> None:
        pid = _id("prop")
        self.proposals[pid] = {
            "proposal_id": pid,
            "kind": "policy_change",
            "target": "wfm_forecast",
            "state": "draft",
            "version": 1,
            "created_by": "account_demo",
            "created_at": _now(),
            "updated_at": _now(),
            "approval_state": "draft",
        }

    # -- helpers --------------------------------------------------------------
    def log_request(self, method: str, path: str, status: int) -> None:
        self.request_log.append(
            {"method": method, "path": path, "status": status, "at": _now()}
        )

    def reset(self) -> None:
        self.__init__()  # type: ignore[assignment]
