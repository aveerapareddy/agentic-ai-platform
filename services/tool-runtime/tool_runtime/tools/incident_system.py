"""Incident system integration (local fixture + simulated API latency)."""

from __future__ import annotations

from typing import Any

from tool_runtime.tools._simulate import incident_key, simulate_latency

# In-memory status store for mutating calls (process-local; not orchestration state).
_STATUS: dict[str, str] = {}


def fetch_incident_metadata(input_payload: dict[str, Any]) -> dict[str, Any]:
    simulate_latency(input_payload, base_ms=20, cap_ms=90)
    iid = incident_key(input_payload)
    if iid.startswith("fail-read"):
        raise ConnectionError("incident system read unavailable (simulated transient)")
    if iid.startswith("bad-read"):
        raise ValueError("malformed incident id for read")
    suffix = iid[-4:] if len(iid) >= 4 else iid
    status = _STATUS.get(iid, "open")
    return {
        "incident_id": iid,
        "severity_inferred": "high" if "crit" in iid.lower() or "sev1" in iid.lower() else "medium",
        "service": f"svc-{suffix}",
        "status": status,
        "provider_id": "incident_system_v1",
        "source": "incident_system_tool",
    }


def update_incident_status(input_payload: dict[str, Any]) -> dict[str, Any]:
    simulate_latency(input_payload, base_ms=30, cap_ms=150)
    iid = incident_key(input_payload)
    new_status = str(input_payload.get("status") or "acknowledged")
    if iid.startswith("deny-mutate"):
        raise PermissionError("mutating action denied by policy gate (simulated)")
    if not input_payload.get("approved", False):
        raise PermissionError("state-changing tool requires approved=true in input")
    _STATUS[iid] = new_status
    return {
        "incident_id": iid,
        "status": new_status,
        "updated": True,
        "provider_id": "incident_system_v1",
        "source": "incident_system_tool",
    }
