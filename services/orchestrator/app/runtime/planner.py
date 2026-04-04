"""Deterministic ExecutionPlan: structured steps only; no LLM (constitution §2.1, §8.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from common_schemas import Execution, ExecutionPlan, PlanId

_INCIDENT_TRIAGE = "incident_triage"


class Planner:
    """Emits workflow-specific plans from structured specs; orchestrator materializes Step rows."""

    def __init__(self, *, default_plan_metadata: dict[str, Any] | None = None) -> None:
        self._meta = default_plan_metadata or {"planner": "deterministic_v1"}

    def create_plan(self, execution: Execution, *, now: datetime | None = None) -> ExecutionPlan:
        """Return plan revision v1: abstract specs only."""
        ts = now or datetime.now(timezone.utc)
        plan_id: PlanId = uuid4()
        if execution.workflow_type == _INCIDENT_TRIAGE:
            return self._plan_incident_triage(execution, plan_id, ts)
        return self._plan_default(execution, plan_id, ts)

    def _plan_incident_triage(self, execution: Execution, plan_id: PlanId, ts: datetime) -> ExecutionPlan:
        analyze_k = str(uuid4())
        gather_k = str(uuid4())
        validate_k = str(uuid4())
        steps: list[dict[str, Any]] = [
            {
                "step_key": analyze_k,
                "step_name": "analyze_incident",
                "kind": "reasoning",
                "agent": "incident_analysis_agent_v1",
                "degraded_allowed": False,
            },
            {
                "step_key": gather_k,
                "step_name": "gather_evidence",
                "kind": "retrieval",
                "agent": "incident_retrieval_agent_v1",
                "degraded_allowed": False,
            },
            {
                "step_key": validate_k,
                "step_name": "validate_incident",
                "kind": "validation",
                "agent": "incident_validation_agent_v1",
                "degraded_allowed": False,
            },
        ]
        dependencies = [
            {"from_step": analyze_k, "to_step": gather_k},
            {"from_step": gather_k, "to_step": validate_k},
        ]
        ordering = {"sequential_groups": [[analyze_k, gather_k, validate_k]]}
        meta = {**dict(self._meta), "planner": "deterministic_incident_triage_v1"}

        return ExecutionPlan(
            plan_id=plan_id,
            execution_id=execution.execution_id,
            parent_plan_id=None,
            plan_version=1,
            revision_reason="initial_plan",
            goal={
                "workflow_type": execution.workflow_type,
                "from_input_keys": list(execution.input.keys()),
            },
            steps=steps,
            dependencies=dependencies,
            ordering=ordering,
            metadata=meta,
            created_at=ts,
        )

    def _plan_default(self, execution: Execution, plan_id: PlanId, ts: datetime) -> ExecutionPlan:
        reasoning_id = str(uuid4())
        validation_id = str(uuid4())
        steps = [
            {
                "step_key": reasoning_id,
                "step_name": "reasoning",
                "kind": "reasoning",
                "agent": "reasoning_agent_v1",
                "degraded_allowed": False,
            },
            {
                "step_key": validation_id,
                "step_name": "validation",
                "kind": "validation",
                "agent": "validation_agent_v1",
                "degraded_allowed": False,
            },
        ]
        dependencies = [{"from_step": reasoning_id, "to_step": validation_id}]
        ordering = {"sequential_groups": [[reasoning_id, validation_id]]}

        return ExecutionPlan(
            plan_id=plan_id,
            execution_id=execution.execution_id,
            parent_plan_id=None,
            plan_version=1,
            revision_reason="initial_plan",
            goal={
                "workflow_type": execution.workflow_type,
                "from_input_keys": list(execution.input.keys()),
            },
            steps=steps,
            dependencies=dependencies,
            ordering=ordering,
            metadata=dict(self._meta),
            created_at=ts,
        )
