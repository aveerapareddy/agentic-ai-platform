from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from common_schemas import ToolCallStatus, ToolInvokeRequest

from tool_runtime.registry import ToolRegistry, build_default_registry
from tool_runtime.service import ToolRuntimeService
from tool_runtime.tools import incident_system


def test_transient_read_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}
    original = incident_system.fetch_incident_metadata

    def flaky(payload: dict) -> dict:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("simulated transient")
        return original(payload)

    monkeypatch.setattr(incident_system, "fetch_incident_metadata", flaky)
    reg = build_default_registry()
    svc = ToolRuntimeService(reg)
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="incident_system_tool",
            input={"incident_id": "inc-retry"},
        ),
        now=datetime.now(timezone.utc),
    )
    assert tc.status == ToolCallStatus.SUCCESS
    assert calls["n"] == 2


def test_policy_denied_skips_handler() -> None:
    svc = ToolRuntimeService()
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="incident_system_tool",
            input={"incident_id": "x"},
            policy_denied=True,
        ),
        now=datetime.now(timezone.utc),
    )
    assert tc.status == ToolCallStatus.REJECTED_BY_POLICY


def test_mutating_tool_requires_approved() -> None:
    svc = ToolRuntimeService()
    tc = svc.invoke(
        ToolInvokeRequest(
            execution_id=uuid4(),
            step_id=uuid4(),
            execution_context_id=uuid4(),
            tool_name="incident_system_update_tool",
            input={"incident_id": "inc-mut", "status": "acknowledged"},
        ),
        now=datetime.now(timezone.utc),
    )
    assert tc.status == ToolCallStatus.FAILURE
    assert tc.error is not None
    assert "approved" in tc.error["message"].lower()
