"""SSE formatting and async poll loop over repository snapshots."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from common_schemas import ExecutionStreamEvent, ExecutionStreamEventType, RequestContext

from gateway.config import Settings
from gateway.services.execution_facade import ExecutionFacade
from gateway.streaming.diff import StreamCursor, diff_stream_events, is_terminal_execution_status
from gateway.tenant_access import assert_execution_visible

try:
    from observability import emit_event, get_registry
except ImportError:  # pragma: no cover

    def emit_event(_event_type: str, **_fields: Any) -> None:
        return None

    def get_registry() -> Any:
        class _Noop:
            def inc(self, *_a: Any, **_k: Any) -> None:
                return None

        return _Noop()


def format_sse_message(event: ExecutionStreamEvent) -> str:
    if event.event_type == ExecutionStreamEventType.HEARTBEAT:
        return ": heartbeat\n\n"
    data = event.model_dump(mode="json")
    return f"event: {event.event_type.value}\ndata: {json.dumps(data, default=str)}\n\n"


async def stream_execution_sse(
    *,
    facade: ExecutionFacade,
    repository: Any,
    execution_id: UUID,
    auth: RequestContext,
    settings: Settings,
) -> AsyncIterator[str]:
    """Poll repository and emit SSE until terminal state or max duration."""
    assert_execution_visible(repository, execution_id, auth)
    poll_s = max(0.1, settings.stream_poll_interval_ms / 1000.0)
    heartbeat_s = max(5.0, float(settings.stream_heartbeat_sec))
    max_duration_s = max(30.0, float(settings.stream_max_duration_sec))

    get_registry().inc("execution_streams_active", labels={})
    emit_event(
        "execution_stream_opened",
        execution_id=str(execution_id),
        tenant_id=auth.tenant.tenant_id,
        principal_id=auth.principal.principal_id,
    )

    cursor = StreamCursor()
    started = asyncio.get_event_loop().time()
    last_heartbeat = started
    terminal_sent = False

    try:
        while True:
            now_loop = asyncio.get_event_loop().time()
            if now_loop - started > max_duration_s:
                emit_event("execution_stream_timeout", execution_id=str(execution_id))
                break

            ex = facade.get_execution(execution_id)
            if ex is None:
                emit_event("execution_stream_error", execution_id=str(execution_id), reason="not_found")
                break

            projection = facade.build_trace_projection(execution_id)
            if projection is None:
                break

            batch = diff_stream_events(execution=ex, trace_projection=projection, cursor=cursor)
            for ev in batch:
                get_registry().inc(
                    "execution_stream_events_total",
                    labels={"event_type": ev.event_type.value},
                )
                yield format_sse_message(ev)
                if ev.is_terminal:
                    terminal_sent = True

            status = ex.status.value if hasattr(ex.status, "value") else str(ex.status)
            if is_terminal_execution_status(status) and (terminal_sent or not batch):
                if not terminal_sent:
                    # Ensure terminal envelope even if status was already terminal at connect.
                    ts = datetime.now(timezone.utc)
                    cursor.sequence += 1
                    etype = ExecutionStreamEventType.EXECUTION_COMPLETED
                    if status == "failed":
                        etype = ExecutionStreamEventType.EXECUTION_FAILED
                    elif status == "cancelled":
                        etype = ExecutionStreamEventType.EXECUTION_CANCELLED
                    term = ExecutionStreamEvent(
                        event_type=etype,
                        execution_id=execution_id,
                        sequence=cursor.sequence,
                        emitted_at=ts,
                        payload={"status": status},
                    )
                    yield format_sse_message(term)
                break

            if now_loop - last_heartbeat >= heartbeat_s:
                hb = ExecutionStreamEvent(
                    event_type=ExecutionStreamEventType.HEARTBEAT,
                    execution_id=execution_id,
                    sequence=cursor.sequence,
                    emitted_at=datetime.now(timezone.utc),
                    payload={},
                )
                yield format_sse_message(hb)
                last_heartbeat = now_loop

            await asyncio.sleep(poll_s)
    except asyncio.CancelledError:
        emit_event("execution_stream_cancelled", execution_id=str(execution_id))
        raise
    except Exception as exc:  # noqa: BLE001
        get_registry().inc("execution_stream_errors_total", labels={"reason": type(exc).__name__})
        emit_event(
            "execution_stream_error",
            execution_id=str(execution_id),
            error_class=type(exc).__name__,
        )
        raise
    finally:
        get_registry().inc("execution_streams_closed_total")
        emit_event("execution_stream_closed", execution_id=str(execution_id))
