"""Replay v2: create child executions with auditable provenance; never mutate source runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from common_schemas import (
    REPLAY_PROVENANCE_INPUT_KEY,
    Execution,
    ExecutionMode,
    ExecutionStatus,
    ReplayCreatedResponse,
    ReplayMode,
    ReplayProvenance,
    ReplayRequest,
)

from app.adapters.repository import Repository
from app.services.execution_service import ExecutionService


class ReplayError(Exception):
    """Base replay failure."""


class ReplayNotFoundError(ReplayError):
    """Source execution or context missing."""


class ReplayValidationError(ReplayError):
    """Invalid replay request for the chosen mode."""


def _strip_replay_metadata(input_payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(input_payload)
    out.pop(REPLAY_PROVENANCE_INPUT_KEY, None)
    return out


def _append_replay_created_event(
    execution: Execution,
    *,
    provenance: ReplayProvenance,
    now: datetime,
) -> Execution:
    overrides_summary: dict[str, Any] = {}
    if provenance.input_overrides:
        overrides_summary = {
            "keys": sorted(provenance.input_overrides.keys()),
            "count": len(provenance.input_overrides),
        }
    row: dict[str, Any] = {
        "event_type": "replay_created",
        "at": now.isoformat(),
        "source_execution_id": str(provenance.source_execution_id),
        "replay_mode": provenance.replay_mode.value,
        "requested_by": provenance.requested_by,
        "reason": provenance.reason,
        "label": provenance.label,
        "environment_target": provenance.environment_target,
        "input_overrides_summary": overrides_summary,
    }
    if provenance.anchor_plan_id is not None:
        row["anchor_plan_id"] = str(provenance.anchor_plan_id)
    return execution.model_copy(
        update={
            "trace_timeline": [*execution.trace_timeline, row],
            "updated_at": now,
        }
    )


class ReplayService:
    """Owns replay construction; gateway and other surfaces call this service only."""

    def __init__(
        self,
        repository: Repository,
        execution_service: ExecutionService,
    ) -> None:
        self._repo = repository
        self._executions = execution_service

    def create_replay(
        self,
        request: ReplayRequest,
        *,
        now: datetime | None = None,
    ) -> ReplayCreatedResponse:
        ts = now or datetime.now(timezone.utc)
        source_id = request.source_execution_id

        src = self._repo.get_execution(source_id)
        if src is None:
            raise ReplayNotFoundError(f"source execution {source_id} not found")
        ctx = self._repo.get_context(src.execution_context_id)
        if ctx is None:
            raise ReplayNotFoundError(f"execution context for {source_id} not found")

        source_before = src.model_dump(mode="json")

        self._validate_request(request)

        base_input = _strip_replay_metadata(dict(src.input))
        input_overrides_applied: dict[str, Any] = {}

        if request.replay_mode == ReplayMode.EXACT:
            replay_input = base_input
        else:
            overrides = dict(request.input_overrides or {})
            if REPLAY_PROVENANCE_INPUT_KEY in overrides:
                raise ReplayValidationError(
                    f"input_overrides must not include reserved key {REPLAY_PROVENANCE_INPUT_KEY!r}"
                )
            input_overrides_applied = overrides
            replay_input = {**base_input, **overrides}

        child = self._executions.create_execution(
            workflow_type=src.workflow_type,
            input_payload={},  # provenance attached after child id is known
            tenant_id=ctx.tenant_id,
            request_id=f"replay-{source_id}",
            environment=request.environment_target,
            policy_scope=ctx.policy_scope,
            principal_id=request.requested_by or ctx.principal_id,
            permissions_scope=dict(ctx.permissions_scope),
            parent_execution_id=source_id,
            execution_mode=request.execution_mode or src.execution_mode,
            feature_flags=dict(ctx.feature_flags) if ctx.feature_flags else None,
            now=ts,
        )

        provenance = ReplayProvenance(
            source_execution_id=source_id,
            replay_mode=request.replay_mode,
            requested_by=request.requested_by,
            reason=request.reason,
            label=request.label,
            input_overrides=input_overrides_applied,
            anchor_plan_id=request.anchor_plan_id or src.current_plan_id,
            environment_target=request.environment_target,
            created_execution_id=child.execution_id,
            created_at=ts,
        )

        replay_input[REPLAY_PROVENANCE_INPUT_KEY] = provenance.model_dump(mode="json")
        child = child.model_copy(update={"input": replay_input})
        child = _append_replay_created_event(child, provenance=provenance, now=ts)
        self._repo.update_execution(child)

        if request.start_execution:
            child = self._executions.start_execution(child.execution_id)

        src_after = self._repo.get_execution(source_id)
        if src_after is None or src_after.model_dump(mode="json") != source_before:
            raise ReplayError("source execution was mutated during replay creation")

        return ReplayCreatedResponse(
            replay_execution_id=child.execution_id,
            source_execution_id=source_id,
            status=child.status.value,
            replay_mode=request.replay_mode,
            provenance=provenance,
        )

    def list_replays_for_source(
        self,
        source_execution_id: UUID,
        *,
        limit: int = 50,
    ) -> list[Execution]:
        return self._repo.list_executions_by_parent(
            parent_execution_id=source_execution_id,
            limit=limit,
        )

    def _validate_request(self, request: ReplayRequest) -> None:
        if request.replay_mode == ReplayMode.EXACT:
            if request.input_overrides:
                raise ReplayValidationError("input_overrides are not allowed for exact replay")
            if request.override_plan is not None:
                raise ReplayValidationError("override_plan is not allowed for exact replay")
        if request.replay_mode == ReplayMode.INVESTIGATIVE:
            if not (request.reason and request.reason.strip()) and not (
                request.label and request.label.strip()
            ):
                raise ReplayValidationError(
                    "investigative replay requires a non-empty reason or label"
                )
        if not request.environment_target.strip():
            raise ReplayValidationError("environment_target is required")
