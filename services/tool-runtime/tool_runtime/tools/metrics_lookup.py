"""Metrics and log snapshot lookup (synthetic operational data)."""

from __future__ import annotations

from typing import Any

from tool_runtime.tools._simulate import incident_key, simulate_latency


def lookup_metrics_snapshot(input_payload: dict[str, Any]) -> dict[str, Any]:
    simulate_latency(input_payload, base_ms=25, cap_ms=110)
    iid = incident_key(input_payload)
    if iid.startswith("timeout-metrics"):
        raise TimeoutError("metrics backend timed out")
    kinds = input_payload.get("signal_types")
    if not isinstance(kinds, list) or not kinds:
        kinds = ["metrics", "logs", "deploy"]
    signals: list[dict[str, Any]] = []
    for i, k in enumerate(kinds):
        if not isinstance(k, str):
            continue
        signals.append(
            {
                "source": k,
                "name": f"{k}_anomaly_{iid[:6]}",
                "detail": f"synthetic {k} window for {iid}",
                "p95_ms": 120 + i * 17,
            },
        )
    return {
        "incident_id": iid,
        "signals": signals,
        "provider_id": "metrics_lookup_v1",
        "source": "metrics_lookup_tool",
    }
