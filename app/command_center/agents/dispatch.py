"""Agent dispatch system using structured tool calls.

This module replaces the regex-based call_agent parsing in base_agent.py
with a structured tool call system using JSON schema validation.

Honesty contract: no tool handler ever returns invented output. Handlers are
either wired (call_agent -> the agent registry; side-effecting tools -> the
bound Engine / document reader) or fail closed with a typed error. The legacy
regex parser exists only behind HELIX_LEGACY_CALL_PARSING=1 and is logged.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from contracts.task import CorrelationContext, TaskRequest
from contracts.toolcall import (
    TOOLS,
    ToolCall,
    ToolCallEnvelope,
    ToolResult,
)

# Per-tool argument schemas: required key -> (type, max length). Validation is
# strict: unknown keys are refused rather than silently ignored (fail closed).
_ARG_SCHEMAS: dict[str, dict[str, tuple[type, int]]] = {
    "call_agent": {"agent_name": (str, 64), "message": (str, 8192)},
    "submit_task": {"task": (str, 2048)},
    "request_approval": {"summary": (str, 2048)},
    "read_document": {"doc_id": (str, 128)},
}


class AgentDispatch:
    """Dispatch system for inter-agent communication.

    This class handles:
    1. Parsing tool calls from LLM responses
    2. Validating tool calls against the registry
    3. Executing tool calls with proper context inheritance
    4. Enforcing depth/cycle limits
    """

    def __init__(
        self,
        engine=None,
        store=None,
        connector_gateway=None,
        max_depth: int = 5,
        document_reader=None,
    ) -> None:
        self._engine = engine
        self._store = store
        self._gateway = connector_gateway
        self._document_reader = document_reader
        self._max_depth = max_depth
        self._depth: int = 0
        self._visited_agents: set[str] = set()

    def parse_tool_calls(self, content: str) -> ToolCallEnvelope:
        """Parse tool calls from LLM response content.

        Args:
            content: The LLM response text.

        Returns:
            ToolCallEnvelope with parsed tool calls.

        If parsing fails, returns envelope with empty tool_calls list
        and content marked as DEAD_LETTER.
        """
        try:
            # Try to extract tool calls from JSON
            data = json.loads(content)
            tool_calls = [ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])]
            return ToolCallEnvelope(
                content=data.get("content", ""),
                tool_calls=tool_calls,
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            # Fallback: return empty envelope, content goes to review queue
            return ToolCallEnvelope(
                content=content,
                tool_calls=[],
            )

    def validate_tool_call(self, tool_call: ToolCall) -> tuple[bool, str]:
        """Validate a tool call against the registry.

        Args:
            tool_call: The tool call to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        tool_def = TOOLS.get(tool_call.tool)
        if tool_def is None:
            return False, f"Unknown tool: {tool_call.tool}"

        args = tool_call.args
        if not isinstance(args, Mapping):
            return False, f"args must be an object, got {type(args).__name__}"

        schema = _ARG_SCHEMAS.get(tool_call.tool, {})
        unknown = sorted(set(args) - set(schema))
        if unknown:
            return False, f"unknown arg(s) for {tool_call.tool}: {', '.join(unknown)}"
        for key, (expected_type, max_len) in schema.items():
            value = args.get(key)
            if value is None:
                return False, f"missing required arg: {key}"
            if not isinstance(value, expected_type) or not value.strip():
                return False, f"arg {key} must be a non-empty {expected_type.__name__}"
            if len(value) > max_len:
                return False, f"arg {key} exceeds {max_len} characters"
        return True, ""

    def check_depth(self) -> bool:
        """Check if we've exceeded max depth.

        Returns:
            True if depth is within limits, False otherwise.
        """
        if self._depth >= self._max_depth:
            return False
        return True

    def check_cycle(self, agent_name: str) -> bool:
        """Check if calling this agent would create a cycle.

        Args:
            agent_name: The name of the agent being called.

        Returns:
            True if no cycle detected, False otherwise.
        """
        if agent_name in self._visited_agents:
            return False
        return True

    async def execute_tool_call(
        self,
        tool_call: ToolCall,
        context: Mapping[str, Any],
    ) -> ToolResult:
        """Execute a tool call with proper context inheritance.

        Args:
            tool_call: The tool call to execute.
            context: The current execution context.

        Returns:
            ToolResult with output or error.
        """
        # Validate tool call
        is_valid, error = self.validate_tool_call(tool_call)
        if not is_valid:
            return ToolResult(
                call_id=tool_call.call_id,
                error=error,
                nature="error",
            )

        # Check depth
        if not self.check_depth():
            return ToolResult(
                call_id=tool_call.call_id,
                error="Max depth exceeded",
                nature="error",
            )

        # Execute based on tool type
        try:
            if tool_call.tool == "call_agent":
                return await self._handle_call_agent(tool_call, context)
            elif tool_call.tool == "submit_task":
                return await self._handle_submit_task(tool_call, context)
            elif tool_call.tool == "request_approval":
                return await self._handle_request_approval(tool_call, context)
            elif tool_call.tool == "read_document":
                return await self._handle_read_document(tool_call, context)
            else:
                return ToolResult(
                    call_id=tool_call.call_id,
                    error=f"Unknown tool: {tool_call.tool}",
                    nature="error",
                )
        except Exception as e:
            return ToolResult(
                call_id=tool_call.call_id,
                error=str(e),
                nature="error",
            )

    async def _handle_call_agent(
        self,
        tool_call: ToolCall,
        context: Mapping[str, Any],
    ) -> ToolResult:
        """Handle call_agent tool call."""
        agent_name = tool_call.args.get("agent_name", "")
        message = tool_call.args.get("message", "")

        # Check for cycles
        if not self.check_cycle(agent_name):
            return ToolResult(
                call_id=tool_call.call_id,
                error=f"Cycle detected: {agent_name} already visited",
                nature="error",
            )

        # Increment depth and add to visited
        self._depth += 1
        self._visited_agents.add(agent_name)

        try:
            from app.command_center.agents.base_agent import AgentRegistry

            agent = AgentRegistry.get_agent(agent_name)
            if agent is None:
                return ToolResult(
                    call_id=tool_call.call_id,
                    error=f"Agent {agent_name!r} is not registered",
                    nature="error",
                )
            # process_request performs a blocking HTTP call to the local model;
            # keep the event loop free.
            output = await asyncio.to_thread(agent.process_request, message)
            return ToolResult(
                call_id=tool_call.call_id,
                output=output,
                nature="model_inference",
            )
        except Exception as exc:
            return ToolResult(
                call_id=tool_call.call_id,
                error=f"call_agent failed: {exc}",
                nature="error",
            )
        finally:
            self._depth -= 1
            self._visited_agents.discard(agent_name)

    async def _handle_submit_task(
        self,
        tool_call: ToolCall,
        context: Mapping[str, Any],
    ) -> ToolResult:
        """Handle submit_task: submit to the bound Engine, or fail closed."""
        return await self._submit_through_engine(
            tool_call, context, default_capability="task_submission"
        )

    async def _handle_request_approval(
        self,
        tool_call: ToolCall,
        context: Mapping[str, Any],
    ) -> ToolResult:
        """Handle request_approval: submit to the bound Engine, or fail closed."""
        return await self._submit_through_engine(
            tool_call, context, default_capability="approval_request"
        )

    async def _handle_read_document(
        self,
        tool_call: ToolCall,
        context: Mapping[str, Any],
    ) -> ToolResult:
        """Handle read_document tool call."""
        doc_id = tool_call.args.get("doc_id", "")
        if self._document_reader is None:
            return ToolResult(
                call_id=tool_call.call_id,
                error="read_document is not available: no document reader bound to this dispatch",
                nature="error",
            )
        try:
            output = await asyncio.to_thread(self._document_reader, doc_id, context)
            return ToolResult(
                call_id=tool_call.call_id,
                output=output,
                nature="verified_fact",
            )
        except Exception as exc:
            return ToolResult(
                call_id=tool_call.call_id,
                error=f"read_document failed: {exc}",
                nature="error",
            )

    async def _submit_through_engine(
        self,
        tool_call: ToolCall,
        context: Mapping[str, Any],
        *,
        default_capability: str,
    ) -> ToolResult:
        """Submit a side-effecting tool call through the bound Engine.

        Fails closed: without an Engine, or without the context keys the
        Engine contract requires, the call is refused — never faked.
        """
        if self._engine is None:
            return ToolResult(
                call_id=tool_call.call_id,
                error=f"{tool_call.tool} is not available: no Engine bound to this dispatch",
                nature="error",
            )

        missing = [
            key
            for key in ("requesting_actor", "owning_role_id", "correlation_id")
            if not str(context.get(key) or "").strip()
        ]
        tenant_id = str(context.get("tenant_id") or "").strip() or None
        client_id = str(context.get("client_id") or "").strip() or None
        if not tenant_id and not client_id:
            # CorrelationContext requires at least one of the two.
            missing.append("tenant_id or client_id")
        if missing:
            return ToolResult(
                call_id=tool_call.call_id,
                error=f"{tool_call.tool} requires context keys: {', '.join(missing)}",
                nature="error",
            )

        now = datetime.now(timezone.utc).isoformat()
        text = tool_call.args.get("task") or tool_call.args.get("summary") or ""
        correlation = CorrelationContext(
            correlation_id=str(context["correlation_id"]),
            idempotency_key=str(context.get("idempotency_key") or tool_call.call_id),
            tenant_id=tenant_id,
            client_id=client_id,
            created_at=now,
        )
        request = TaskRequest(
            request_id=f"req-{uuid.uuid4().hex[:12]}",
            correlation=correlation,
            requesting_actor=str(context["requesting_actor"]),
            owning_role_id=str(context["owning_role_id"]),
            capability=str(context.get("capability") or default_capability),
            input_payload={
                "text": text,
                "source": "agent_dispatch",
                "tool_call_id": tool_call.call_id,
                "data_classification": context.get("data_classification") or "internal",
            },
            requires_approval=True,
            status="proposed",
            created_at=now,
        )
        try:
            workflow = await asyncio.to_thread(self._engine.submit, request)
        except Exception as exc:
            return ToolResult(
                call_id=tool_call.call_id,
                error=f"{tool_call.tool} engine submit failed: {exc}",
                nature="error",
            )
        return ToolResult(
            call_id=tool_call.call_id,
            output={
                "workflow_id": getattr(workflow, "workflow_id", None),
                "state": str(getattr(workflow, "state", "unknown")),
                "requires_approval": True,
            },
            nature="model_inference",
        )

    async def process_tool_calls(
        self,
        envelope: ToolCallEnvelope,
        context: Mapping[str, Any],
    ) -> list[ToolResult]:
        """Process all tool calls in an envelope.

        Args:
            envelope: The tool call envelope.
            context: The current execution context.

        Returns:
            List of ToolResult objects.
        """
        results = []
        for tool_call in envelope.tool_calls:
            result = await self.execute_tool_call(tool_call, context)
            results.append(result)
        return results


def parse_legacy_calls(content: str) -> list[dict]:
    """Legacy regex-based parser for backward compatibility.

    This is kept behind HELIX_LEGACY_CALL_PARSING=1 for migration purposes.

    Args:
        content: The LLM response text.

    Returns:
        List of parsed call dictionaries.
    """
    import re

    call_pattern = r'call_agent\((["\'])([A-Z_]+)\1,\s*(["\'])(.*?)\3\)'
    matches = re.findall(call_pattern, content, re.DOTALL)
    return [
        {
            "agent": agent,
            "message": msg,
        }
        for _, agent, _, msg in matches
    ]
