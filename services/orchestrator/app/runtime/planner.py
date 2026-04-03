"""Deterministic ExecutionPlan: structured steps only; no LLM (constitution §2.1, §8.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from common_schemas import Execution, ExecutionPlan, PlanId


class Planner:
    """Emits a minimal two-step plan: reasoning then validation (constitution §6.1)."""

    def __init__(self, *, default_plan_metadata: dict[str, Any] | None = None) -> None:
        self._meta = default_plan_metadata or {"planner": "deterministic_v1"}

    def create_plan(self, execution: Execution, *, now: datetime | None = None) -> ExecutionPlan:
        """Return plan revision v1: abstract specs only; orchestrator materializes Step rows."""
        ts = now or datetime.now(timezone.utc)
        plan_id: PlanId = uuid4()
        reasoning_id = str(uuid4())
        validation_id = str(uuid4())
        steps = [
            {
                "step_key": reasoning_id,
                "kind": "reasoning",
                "agent": "reasoning_agent_v1",
                "degraded_allowed": False,
            },
            {
                "step_key": validation_id,
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
