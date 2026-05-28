"""Temporary execution runtime metadata bridge in executions.input (until dedicated columns)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from common_schemas import Execution

_ORCH_RUNTIME_META_KEY = "__orch_runtime_meta__"


def read_runtime_meta(execution: Execution) -> dict[str, Any]:
    raw = execution.input.get(_ORCH_RUNTIME_META_KEY)
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def apply_runtime_meta(execution: Execution, **patch: Any) -> Execution:
    meta = read_runtime_meta(execution)
    for key, value in patch.items():
        if value is None:
            meta.pop(key, None)
        else:
            meta[key] = value
    new_input = dict(execution.input)
    if meta:
        new_input[_ORCH_RUNTIME_META_KEY] = meta
    else:
        new_input.pop(_ORCH_RUNTIME_META_KEY, None)
    return execution.model_copy(update={"input": new_input})


def is_cancellation_requested(execution: Execution) -> bool:
    return bool(read_runtime_meta(execution).get("cancellation_requested"))


def queued_at(execution: Execution) -> str | None:
    val = read_runtime_meta(execution).get("queued_at")
    return str(val) if val is not None else None


def mark_queued(execution: Execution, *, at: datetime) -> Execution:
    return apply_runtime_meta(execution, queued_at=at.isoformat(), cancellation_requested=False)


def mark_worker_started(execution: Execution, *, worker_id: str, at: datetime) -> Execution:
    return apply_runtime_meta(
        execution,
        worker_id=worker_id,
        worker_started_at=at.isoformat(),
    )


def request_cancellation_meta(execution: Execution, *, at: datetime, reason: str = "operator") -> Execution:
    return apply_runtime_meta(
        execution,
        cancellation_requested=True,
        cancellation_requested_at=at.isoformat(),
        cancellation_reason=reason,
    )
