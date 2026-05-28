"""Shared simulation helpers for realistic tool behavior."""

from __future__ import annotations

import hashlib
import time
from typing import Any


def simulate_latency(input_payload: dict[str, Any], *, base_ms: int = 15, cap_ms: int = 120) -> None:
    """Deterministic short delay from incident id (no randomness)."""
    raw = str(input_payload.get("incident_id") or input_payload.get("id") or "x")
    digest = int(hashlib.sha256(raw.encode()).hexdigest()[:4], 16)
    ms = base_ms + (digest % max(1, cap_ms - base_ms))
    time.sleep(ms / 1000.0)


def incident_key(input_payload: dict[str, Any]) -> str:
    return str(input_payload.get("incident_id") or input_payload.get("id") or "unknown")
