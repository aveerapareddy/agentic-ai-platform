"""Registered tools: metadata + handlers (no orchestration state)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from common_schemas import RegisteredTool, ToolIdempotency, ToolRetryPolicy, ToolSideEffectClass

from tool_runtime.tools import cloud_cost, incident_system, metrics_lookup

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


class ToolRegistry:
    """In-memory registry; production would load from config with same contracts."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[RegisteredTool, ToolHandler]] = {}

    def register(self, meta: RegisteredTool, handler: ToolHandler) -> None:
        self._tools[meta.tool_name] = (meta, handler)

    def get(self, tool_name: str) -> tuple[RegisteredTool, ToolHandler] | None:
        return self._tools.get(tool_name)

    def list_registered(self) -> list[RegisteredTool]:
        return [meta for meta, _ in self._tools.values()]


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    read_policy = ToolRetryPolicy(max_retries=2, backoff_ms=100)
    mutate_policy = ToolRetryPolicy(max_retries=0, backoff_ms=0)

    reg.register(
        RegisteredTool(
            tool_name="incident_system_tool",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            timeout_bounds_ms=3_000,
            provider_id="incident_system_v1",
            retry_policy=read_policy,
            description="Fetch incident metadata from incident system (local fixture).",
        ),
        incident_system.fetch_incident_metadata,
    )
    reg.register(
        RegisteredTool(
            tool_name="incident_system_update_tool",
            side_effect_class=ToolSideEffectClass.STATE_CHANGING,
            idempotency=ToolIdempotency.NON_IDEMPOTENT,
            timeout_bounds_ms=5_000,
            provider_id="incident_system_v1",
            retry_policy=mutate_policy,
            description="Update incident status (requires approved=true; governed mutating example).",
        ),
        incident_system.update_incident_status,
    )
    reg.register(
        RegisteredTool(
            tool_name="metrics_lookup_tool",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            timeout_bounds_ms=4_000,
            provider_id="metrics_lookup_v1",
            retry_policy=read_policy,
            description="Synthetic metrics/log snapshot for an incident.",
        ),
        metrics_lookup.lookup_metrics_snapshot,
    )
    reg.register(
        RegisteredTool(
            tool_name="cloud_cost_tool",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            timeout_bounds_ms=4_000,
            provider_id="cloud_cost_v1",
            retry_policy=read_policy,
            description="Cloud cost attribution snapshot with anomaly flag.",
        ),
        cloud_cost.fetch_cost_snapshot,
    )

    # Legacy names used by incident_triage orchestrator path (aliases).
    reg.register(
        RegisteredTool(
            tool_name="incident_metadata_tool",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            timeout_bounds_ms=3_000,
            provider_id="incident_system_v1",
            retry_policy=read_policy,
            description="Alias for incident_system_tool (Phase 4 compatibility).",
        ),
        incident_system.fetch_incident_metadata,
    )
    reg.register(
        RegisteredTool(
            tool_name="signal_lookup_tool",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            timeout_bounds_ms=4_000,
            provider_id="metrics_lookup_v1",
            retry_policy=read_policy,
            description="Alias for metrics_lookup_tool (Phase 4 compatibility).",
        ),
        metrics_lookup.lookup_metrics_snapshot,
    )
    return reg
