"""Structured operational events (stdout JSON lines). No prompt or secret dumping."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

_FORBIDDEN_KEYS = frozenset({"prompt", "messages", "api_key", "authorization"})


def emit_event(event_type: str, **fields: Any) -> None:
    """Emit one structured JSON log line. Values must be JSON-serializable."""
    safe: dict[str, Any] = {}
    for key, value in fields.items():
        if key.lower() in _FORBIDDEN_KEYS:
            continue
        safe[key] = value
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        **safe,
    }
    sys.stdout.write(json.dumps(row, default=str) + "\n")
    sys.stdout.flush()
