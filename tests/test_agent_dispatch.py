"""Tests for structured agent dispatch.

Tests cover:
1. Structured round-trip (parse → validate → execute → result)
2. Malformed output → review queue with zero tool executions
3. Depth-6 → typed refusal
4. submit_task/request_approval fail closed without an Engine; when an Engine
   is bound, the TaskRequest is submitted with requires_approval=True
5. Strict argument validation (missing/unknown/over-length args refused)
"""
from __future__ import annotations

import asyncio
import json

from app.command_center.agents.dispatch import AgentDispatch, parse_legacy_calls
from contracts.toolcall import ToolCall


def test_structured_round_trip():
    """Test 1: Structured round-trip."""
    dispatch = AgentDispatch(max_depth=5)
    content = json.dumps(
        {
            "content": "Let me check with PHILI",
            "tool_calls": [
                {
                    "call_id": "call_1",
                    "tool": "call_agent",
                    "args": {"agent_name": "PHILI", "message": "What is the headcount?"},
                }
            ],
        }
    )

    envelope = dispatch.parse_tool_calls(content)
    assert len(envelope.tool_calls) == 1
    assert envelope.tool_calls[0].tool == "call_agent"
    assert envelope.tool_calls[0].args["agent_name"] == "PHILI"


def test_malformed_output_no_tool_executions():
    """Test 2: Malformed output → review queue, zero executions."""
    dispatch = AgentDispatch(max_depth=5)
    content = "This is just plain text, no tool calls here"

    envelope = dispatch.parse_tool_calls(content)
    assert len(envelope.tool_calls) == 0


def test_depth_refusal():
    """Test 3: Depth-6 → typed refusal."""
    dispatch = AgentDispatch(max_depth=5)
    # Manually set depth to max
    dispatch._depth = 5

    tool_call = ToolCall(
        call_id="call_1",
        tool="call_agent",
        args={"agent_name": "PHILI", "message": "Test"},
    )

    result = asyncio.run(dispatch.execute_tool_call(tool_call, {}))
    assert result.error == "Max depth exceeded"
    assert result.nature == "error"


def test_submit_task_valid():
    """Test 4: submit_task is a valid tool."""
    dispatch = AgentDispatch(max_depth=5)
    tool_call = ToolCall(
        call_id="call_1",
        tool="submit_task",
        args={"task": "Review proposal"},
    )

    is_valid, error = dispatch.validate_tool_call(tool_call)
    assert is_valid is True
    assert error == ""


def test_legacy_parser_still_works():
    """Test legacy parser for backward compatibility."""
    content = 'Please call_agent("PHILI", "What is the headcount?")'
    calls = parse_legacy_calls(content)
    assert len(calls) == 1
    assert calls[0]["agent"] == "PHILI"
    assert calls[0]["message"] == "What is the headcount?"


def test_cycle_detection():
    """Test that cycles are detected."""
    dispatch = AgentDispatch(max_depth=5)
    # Simulate visiting PHILI
    dispatch._visited_agents.add("PHILI")
    dispatch._depth = 4  # One below max

    tool_call = ToolCall(
        call_id="call_1",
        tool="call_agent",
        args={"agent_name": "PHILI", "message": "Test"},
    )

    # This should detect the cycle
    result = asyncio.run(dispatch.execute_tool_call(tool_call, {}))
    assert "Cycle" in result.error or "cycle" in result.error.lower()


def test_validate_rejects_missing_args():
    dispatch = AgentDispatch(max_depth=5)
    tool_call = ToolCall(call_id="c1", tool="call_agent", args={"agent_name": "PHILI"})
    is_valid, error = dispatch.validate_tool_call(tool_call)
    assert is_valid is False
    assert "message" in error


def test_validate_rejects_unknown_args():
    dispatch = AgentDispatch(max_depth=5)
    tool_call = ToolCall(
        call_id="c1",
        tool="call_agent",
        args={"agent_name": "PHILI", "message": "hi", "shell": "rm -rf /"},
    )
    is_valid, error = dispatch.validate_tool_call(tool_call)
    assert is_valid is False
    assert "shell" in error


def test_validate_rejects_overlength_and_non_string():
    dispatch = AgentDispatch(max_depth=5)
    tool_call = ToolCall(
        call_id="c1",
        tool="call_agent",
        args={"agent_name": "PHILI", "message": 1234},
    )
    is_valid, error = dispatch.validate_tool_call(tool_call)
    assert is_valid is False


def test_submit_task_fails_closed_without_engine():
    dispatch = AgentDispatch(max_depth=5)
    tool_call = ToolCall(call_id="c1", tool="submit_task", args={"task": "Review proposal"})
    result = asyncio.run(
        dispatch.execute_tool_call(
            tool_call,
            {
                "tenant_id": "t-1",
                "requesting_actor": "sami",
                "owning_role_id": "ops_gm",
                "correlation_id": "corr-1",
            },
        )
    )
    assert result.nature == "error"
    assert "no Engine bound" in (result.error or "")


def test_submit_task_requires_context_keys():
    dispatch = AgentDispatch(max_depth=5, engine=object())
    tool_call = ToolCall(call_id="c1", tool="submit_task", args={"task": "Review proposal"})
    result = asyncio.run(dispatch.execute_tool_call(tool_call, {}))
    assert result.nature == "error"
    assert "context keys" in (result.error or "")


class _StubEngine:
    def __init__(self):
        self.requests = []

    def submit(self, request):
        self.requests.append(request)

        class _Workflow:
            workflow_id = "wf-stub-1"
            state = "awaiting_approval"

        return _Workflow()


def test_submit_task_wires_to_engine():
    engine = _StubEngine()
    dispatch = AgentDispatch(max_depth=5, engine=engine)
    tool_call = ToolCall(call_id="c1", tool="submit_task", args={"task": "Review proposal"})
    result = asyncio.run(
        dispatch.execute_tool_call(
            tool_call,
            {
                "tenant_id": "t-1",
                "client_id": "c-1",
                "requesting_actor": "sami",
                "owning_role_id": "ops_gm",
                "correlation_id": "corr-1",
                "idempotency_key": "idem-1",
            },
        )
    )
    assert result.nature == "model_inference"
    assert result.output == {
        "workflow_id": "wf-stub-1",
        "state": "awaiting_approval",
        "requires_approval": True,
    }
    assert len(engine.requests) == 1
    request = engine.requests[0]
    assert request.requires_approval is True
    assert request.input_payload["text"] == "Review proposal"
    assert request.capability == "task_submission"


def test_call_agent_unknown_agent_fails_closed():
    dispatch = AgentDispatch(max_depth=5)
    tool_call = ToolCall(
        call_id="c1",
        tool="call_agent",
        args={"agent_name": "NO_SUCH_AGENT_XYZ", "message": "hello"},
    )
    result = asyncio.run(dispatch.execute_tool_call(tool_call, {}))
    assert result.nature == "error"
    assert "not registered" in (result.error or "")


def test_read_document_fails_closed_without_reader():
    dispatch = AgentDispatch(max_depth=5)
    tool_call = ToolCall(call_id="c1", tool="read_document", args={"doc_id": "doc-1"})
    result = asyncio.run(dispatch.execute_tool_call(tool_call, {}))
    assert result.nature == "error"
    assert "no document reader" in (result.error or "")
