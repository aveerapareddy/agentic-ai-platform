"""Diff repository snapshots into bounded stream events."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from common_schemas import Execution, ExecutionStatus, ExecutionStreamEvent, ExecutionStreamEventType

_TERMINAL_STATUSES = frozenset(
    {
        ExecutionStatus.COMPLETED.value,
        ExecutionStatus.FAILED.value,
        ExecutionStatus.CANCELLED.value,
    },
)


def is_terminal_execution_status(status: str) -> bool:
    return status in _TERMINAL_STATUSES


def _bounded_trace_payload(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "event_type": row.get("event_type"),
        "at": row.get("at"),
    }
    for key in ("step_id", "planner_step_name", "workflow_type", "status", "path", "task", "tool_name"):
        if key in row:
            out[key] = row[key]
    detail = {k: v for k, v in row.items() if k not in ("event_type", "at")}
    if detail:
        raw = json.dumps(detail, default=str)
        if len(raw) > 800:
            out["detail_excerpt"] = raw[:800]
        else:
            out["detail"] = detail
    return out


def _step_payload(step: Any, step_result: Any | None) -> dict[str, Any]:
    st = step.model_dump(mode="json") if hasattr(step, "model_dump") else dict(step)
    payload: dict[str, Any] = {
        "step_id": st.get("step_id"),
        "status": st.get("status"),
        "step_type": st.get("step_type"),
        "planner_step_name": (st.get("input") or {}).get("planner_step_name")
        if isinstance(st.get("input"), dict)
        else None,
    }
    if step_result is not None:
        sr = (
            step_result.model_dump(mode="json")
            if hasattr(step_result, "model_dump")
            else dict(step_result)
        )
        payload["confidence_score"] = sr.get("confidence_score")
        vo = sr.get("validation_outcome")
        if isinstance(vo, dict):
            payload["validation_status"] = vo.get("status")
    return payload


@dataclass
class StreamCursor:
    execution_status: str | None = None
    timeline_len: int = 0
    step_status_by_id: dict[str, str] = field(default_factory=dict)
    approval_count: int = 0
    sequence: int = 0


def diff_stream_events(
    *,
    execution: Execution,
    trace_projection: dict[str, Any],
    cursor: StreamCursor,
    now: datetime | None = None,
) -> list[ExecutionStreamEvent]:
    """Return new events since cursor; mutates cursor sequence."""
    ts = now or datetime.now(timezone.utc)
    eid = execution.execution_id
    events: list[ExecutionStreamEvent] = []

    def emit(etype: ExecutionStreamEventType, payload: dict[str, Any]) -> None:
        cursor.sequence += 1
        events.append(
            ExecutionStreamEvent(
                event_type=etype,
                execution_id=eid,
                sequence=cursor.sequence,
                emitted_at=ts,
                payload=payload,
            ),
        )

    status = execution.status.value if hasattr(execution.status, "value") else str(execution.status)
    if cursor.execution_status != status:
        cursor.execution_status = status
        emit(
            ExecutionStreamEventType.EXECUTION_UPDATED,
            {
                "status": status,
                "workflow_type": execution.workflow_type,
                "updated_at": execution.updated_at.isoformat(),
            },
        )
        if status == ExecutionStatus.AWAITING_APPROVAL.value:
            gov = execution.result.get("governance") if isinstance(execution.result, dict) else None
            emit(
                ExecutionStreamEventType.APPROVAL_REQUIRED,
                {
                    "status": status,
                    "governance": dict(gov) if isinstance(gov, dict) else {},
                },
            )
        if status == ExecutionStatus.COMPLETED.value:
            emit(
                ExecutionStreamEventType.EXECUTION_COMPLETED,
                {"status": status, "result_summary": _result_summary(execution)},
            )
        elif status == ExecutionStatus.FAILED.value:
            emit(
                ExecutionStreamEventType.EXECUTION_FAILED,
                {"status": status, "result_summary": _result_summary(execution)},
            )
        elif status == ExecutionStatus.CANCELLED.value:
            emit(
                ExecutionStreamEventType.EXECUTION_CANCELLED,
                {"status": status, "cancelled_at": execution.cancelled_at.isoformat() if execution.cancelled_at else None},
            )

    timeline = trace_projection.get("timeline") or []
    if isinstance(timeline, list):
        for idx in range(cursor.timeline_len, len(timeline)):
            row = timeline[idx]
            if not isinstance(row, dict):
                continue
            et = str(row.get("event_type") or "")
            emit(ExecutionStreamEventType.TRACE_EVENT, _bounded_trace_payload(row))
            if et == "replay_created":
                emit(
                    ExecutionStreamEventType.REPLAY_CREATED,
                    {
                        "replay_execution_id": row.get("replay_execution_id"),
                        "source_execution_id": row.get("source_execution_id") or str(eid),
                        "replay_mode": row.get("replay_mode"),
                    },
                )
        cursor.timeline_len = len(timeline)

    steps = trace_projection.get("steps") or []
    if isinstance(steps, list):
        for row in steps:
            if not isinstance(row, dict):
                continue
            step = row.get("step")
            if not isinstance(step, dict):
                continue
            sid = str(step.get("step_id") or "")
            st_status = str(step.get("status") or "")
            if not sid:
                continue
            prev = cursor.step_status_by_id.get(sid)
            if prev != st_status:
                cursor.step_status_by_id[sid] = st_status
                sr = row.get("step_result")
                emit(
                    ExecutionStreamEventType.STEP_UPDATED,
                    _step_payload(step, sr),
                )

    approvals = trace_projection.get("approvals") or []
    if isinstance(approvals, list) and len(approvals) > cursor.approval_count:
        cursor.approval_count = len(approvals)
        last = approvals[-1]
        if isinstance(last, dict):
            emit(
                ExecutionStreamEventType.EXECUTION_UPDATED,
                {
                    "approval_recorded": True,
                    "decision": last.get("decision"),
                    "approver": last.get("approver"),
                },
            )

    return events


def _result_summary(execution: Execution) -> dict[str, Any]:
    res = execution.result
    if not isinstance(res, dict):
        return {}
    keys = ("outcome", "workflow_type", "validation_status", "likely_cause", "confidence_score", "confidence")
    return {k: res[k] for k in keys if k in res}
