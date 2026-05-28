"""Facade: invoke tools with default or injected registry."""

from __future__ import annotations

from datetime import datetime, timezone

from common_schemas import ToolCall, ToolInvokeRequest

from tool_runtime.executor import ToolExecutor
from tool_runtime.registry import ToolRegistry, build_default_registry


class ToolRuntimeService:
    """Owns tool execution; orchestrator calls `invoke` only (constitution §8.2)."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self._executor = ToolExecutor(registry or build_default_registry())

    def invoke(self, request: ToolInvokeRequest, *, now: datetime | None = None) -> ToolCall:
        ts = now or datetime.now(timezone.utc)
        try:
            from observability import emit_event, get_registry, observe_latency_ms

            emit_event(
                "tool_invoke",
                execution_id=str(request.execution_id),
                step_id=str(request.step_id),
                tool_name=request.tool_name,
            )
            import time

            started = time.perf_counter()
            tc = self._executor.execute(request, now=ts)
            latency_ms = float(tc.latency_ms or int((time.perf_counter() - started) * 1000))
            observe_latency_ms("tool_invoke", latency_ms, labels={"tool": request.tool_name})
            get_registry().inc("tool_invocations_total", labels={"tool": request.tool_name, "status": tc.status.value})
            return tc
        except ImportError:
            return self._executor.execute(request, now=ts)
