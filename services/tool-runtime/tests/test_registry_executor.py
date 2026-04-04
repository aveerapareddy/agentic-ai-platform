"""Tool registry and deterministic execution."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import ToolCallStatus, ToolInvokeRequest

from tool_runtime.registry import ToolRegistry, build_default_registry
from tool_runtime.service import ToolRuntimeService


def test_default_registry_lists_two_tools() -> None:
    reg = build_default_registry()
    names = {m.tool_name for m in reg.list_registered()}
    assert names == {"incident_metadata_tool", "signal_lookup_tool"}
    for m in reg.list_registered():
        assert m.side_effect_class.value == "read_only"
        assert m.idempotency.value == "idempotent"


def test_incident_metadata_tool_success() -> None:
    svc = ToolRuntimeService()
    now = datetime.now(timezone.utc)
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="incident_metadata_tool",
            input={"incident_id": "inc-42"},
        ),
        now=now,
    )
    assert tc.status == ToolCallStatus.SUCCESS
    assert tc.output is not None
    assert tc.output.get("incident_id") == "inc-42"
    assert tc.output.get("service")


def test_signal_lookup_tool_success() -> None:
    svc = ToolRuntimeService()
    now = datetime.now(timezone.utc)
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="signal_lookup_tool",
            input={"incident_id": "x", "signal_types": ["metrics"]},
        ),
        now=now,
    )
    assert tc.status == ToolCallStatus.SUCCESS
    assert isinstance(tc.output, dict)
    assert len(tc.output.get("signals", [])) >= 1


def test_unknown_tool_failure() -> None:
    svc = ToolRuntimeService()
    now = datetime.now(timezone.utc)
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="no_such_tool",
            input={"incident_id": "a"},
        ),
        now=now,
    )
    assert tc.status == ToolCallStatus.FAILURE
    assert tc.error is not None


def test_missing_incident_id_failure() -> None:
    svc = ToolRuntimeService()
    now = datetime.now(timezone.utc)
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="incident_metadata_tool",
            input={},
        ),
        now=now,
    )
    assert tc.status == ToolCallStatus.FAILURE


def test_custom_registry_unknown() -> None:
    empty = ToolRegistry()
    svc = ToolRuntimeService(registry=empty)
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="incident_metadata_tool",
            input={"incident_id": "a"},
        ),
        now=datetime.now(timezone.utc),
    )
    assert tc.status == ToolCallStatus.FAILURE
