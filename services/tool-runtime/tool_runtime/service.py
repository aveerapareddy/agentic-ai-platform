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
        return self._executor.execute(request, now=ts)
