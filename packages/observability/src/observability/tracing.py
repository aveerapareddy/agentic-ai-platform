"""OpenTelemetry-lite span helpers (no external OTel SDK)."""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator

from observability.events import emit_event


@dataclass
class Span:
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=time.perf_counter)
    ended: bool = False

    def end(self, *, status: str = "ok", error: str | None = None) -> None:
        if self.ended:
            return
        self.ended = True
        duration_ms = (time.perf_counter() - self.started_at) * 1000.0
        payload: dict[str, Any] = {
            "span": self.name,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            **self.attributes,
        }
        if error:
            payload["error"] = error[:500]
        emit_event("span_completed", **payload)


@contextmanager
def span(name: str, **attributes: Any) -> Generator[Span, None, None]:
    s = Span(name=name, attributes=dict(attributes))
    try:
        yield s
    except Exception as exc:  # noqa: BLE001
        s.end(status="error", error=str(exc))
        raise
    else:
        s.end(status="ok")
