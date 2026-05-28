"""Cloud cost attribution snapshot (synthetic cost data)."""

from __future__ import annotations

from typing import Any

from tool_runtime.tools._simulate import incident_key, simulate_latency


def fetch_cost_snapshot(input_payload: dict[str, Any]) -> dict[str, Any]:
    simulate_latency(input_payload, base_ms=18, cap_ms=95)
    iid = incident_key(input_payload)
    if iid.startswith("fail-cost"):
        raise ConnectionError("cost API unavailable (simulated transient)")
    service = str(input_payload.get("service") or f"svc-{iid[-4:]}")
    daily_usd = round(42.5 + len(iid) % 20, 2)
    return {
        "incident_id": iid,
        "service": service,
        "daily_cost_usd": daily_usd,
        "anomaly": daily_usd > 55.0,
        "attribution_window_hours": 24,
        "provider_id": "cloud_cost_v1",
        "source": "cloud_cost_tool",
    }
