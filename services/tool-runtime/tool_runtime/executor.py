"""Execute invoke requests; produce ToolCall audit rows."""

from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4

from common_schemas import (
    ToolCall,
    ToolCallStatus,
    ToolIdempotency,
    ToolInvokeRequest,
    ToolCallId,
    ToolSideEffectClass,
)

from tool_runtime.registry import ToolRegistry


class ToolExecutor:
    """Validates registration, runs handler, returns ToolCall (success or failure)."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, request: ToolInvokeRequest, *, now: datetime) -> ToolCall:
        entry = self._registry.get(request.tool_name)
        started = time.perf_counter_ns()
        tcid: ToolCallId = uuid4()

        if entry is None:
            ended = time.perf_counter_ns()
            latency_ms = max(0, (ended - started) // 1_000_000)
            return ToolCall(
                tool_call_id=tcid,
                execution_id=request.execution_id,
                step_id=request.step_id,
                execution_context_id=request.execution_context_id,
                action_proposal_id=request.action_proposal_id,
                tool_name=request.tool_name,
                side_effect_class=ToolSideEffectClass.READ_ONLY,
                idempotency=ToolIdempotency.IDEMPOTENT,
                input=dict(request.input),
                output=None,
                status=ToolCallStatus.FAILURE,
                latency_ms=latency_ms,
                error={"code": "unknown_tool", "message": f"tool not registered: {request.tool_name}"},
                created_at=now,
                updated_at=now,
            )

        meta, handler = entry
        try:
            if "incident_id" not in request.input and "id" not in request.input:
                raise ValueError("incident_id or id is required in tool input")
            out = handler(dict(request.input))
            if not isinstance(out, dict):
                raise TypeError("tool handler must return dict")
        except Exception as exc:  # noqa: BLE001 — boundary: normalize to ToolCall failure
            ended = time.perf_counter_ns()
            latency_ms = max(0, (ended - started) // 1_000_000)
            return ToolCall(
                tool_call_id=tcid,
                execution_id=request.execution_id,
                step_id=request.step_id,
                execution_context_id=request.execution_context_id,
                action_proposal_id=request.action_proposal_id,
                tool_name=request.tool_name,
                side_effect_class=meta.side_effect_class,
                idempotency=meta.idempotency,
                input=dict(request.input),
                output=None,
                status=ToolCallStatus.FAILURE,
                latency_ms=latency_ms,
                error={"code": "tool_execution_error", "message": str(exc)},
                created_at=now,
                updated_at=now,
            )

        ended = time.perf_counter_ns()
        latency_ms = max(0, (ended - started) // 1_000_000)
        return ToolCall(
            tool_call_id=tcid,
            execution_id=request.execution_id,
            step_id=request.step_id,
            execution_context_id=request.execution_context_id,
            action_proposal_id=request.action_proposal_id,
            tool_name=request.tool_name,
            side_effect_class=meta.side_effect_class,
            idempotency=meta.idempotency,
            input=dict(request.input),
            output=out,
            status=ToolCallStatus.SUCCESS,
            latency_ms=latency_ms,
            error=None,
            created_at=now,
            updated_at=now,
        )
