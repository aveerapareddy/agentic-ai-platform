"""Registered tools: metadata + pure handlers (no orchestration state)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from common_schemas import RegisteredTool, ToolIdempotency, ToolSideEffectClass

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


def _incident_metadata(input_payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = str(input_payload.get("incident_id") or input_payload.get("id") or "unknown")
    # Deterministic pseudo-metadata (no external I/O).
    suffix = incident_id[-4:] if len(incident_id) >= 4 else incident_id
    return {
        "incident_id": incident_id,
        "severity_inferred": "high" if "crit" in incident_id.lower() or "sev1" in incident_id.lower() else "medium",
        "service": f"svc-{suffix}",
        "status": "open",
        "source": "incident_metadata_tool",
    }


def _signal_lookup(input_payload: dict[str, Any]) -> dict[str, Any]:
    incident_id = str(input_payload.get("incident_id") or input_payload.get("id") or "unknown")
    kinds = input_payload.get("signal_types")
    if not isinstance(kinds, list) or not kinds:
        kinds = ["metrics", "logs", "deploy"]
    signals: list[dict[str, str]] = []
    for i, k in enumerate(kinds):
        if not isinstance(k, str):
            continue
        signals.append(
            {
                "source": k,
                "name": f"{k}_anomaly_{incident_id[:6]}",
                "detail": f"deterministic correlation window for {incident_id} ({i})",
            },
        )
    return {"incident_id": incident_id, "signals": signals, "source": "signal_lookup_tool"}


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        RegisteredTool(
            tool_name="incident_metadata_tool",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            timeout_bounds_ms=5_000,
            description="Read-only incident record fields (Phase 4 local).",
        ),
        _incident_metadata,
    )
    reg.register(
        RegisteredTool(
            tool_name="signal_lookup_tool",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            timeout_bounds_ms=5_000,
            description="Deterministic signal catalog for an incident (Phase 4 local).",
        ),
        _signal_lookup,
    )
    return reg
