"""Execution loop: explicit transitions, repository-backed state, no policy/tools (constitution §8.2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from common_schemas import (
    Execution,
    ExecutionPlan,
    ExecutionStatus,
    Step,
    StepDependency,
    StepStatus,
    StepType,
)

from app.adapters.repository import Repository
from app.config import OrchestratorSettings
from app.runtime.planner import Planner
from app.runtime.state_machine import (
    InvalidStatusTransitionError,
    is_execution_terminal,
    validate_execution_transition,
    validate_step_transition,
)
from app.runtime.step_executor import StepExecutor


class OrchestrationError(RuntimeError):
    """Raised when the run cannot make progress (recorded; may lead to FAILED)."""


def _append_timeline(
    execution: Execution,
    event_type: str,
    detail: dict[str, Any],
    now: datetime,
) -> Execution:
    """Append one trace row (constitution §4.1, §5.3)."""
    row: dict[str, Any] = {"event_type": event_type, "at": now.isoformat(), **detail}
    return execution.model_copy(
        update={
            "trace_timeline": [*execution.trace_timeline, row],
            "updated_at": now,
        }
    )


class ExecutionEngine:
    """Deterministic control layer; AI does not own lifecycle (constitution §2.3, §8.4)."""

    def __init__(
        self,
        repository: Repository,
        *,
        planner: Planner | None = None,
        step_executor: StepExecutor | None = None,
        settings: OrchestratorSettings | None = None,
    ) -> None:
        self._repo = repository
        self._planner = planner or Planner()
        self._executor = step_executor or StepExecutor()
        self._settings = settings or OrchestratorSettings()

    def run_execution(self, execution_id: UUID) -> Execution:
        """Drive execution through planning, executing, validating, to COMPLETED or FAILED."""
        ex = self._repo.get_execution(execution_id)
        if ex is None:
            msg = f"execution not found: {execution_id}"
            raise KeyError(msg)

        now = datetime.now(timezone.utc)

        if is_execution_terminal(ex.status):
            return ex

        if ex.status == ExecutionStatus.CREATED:
            validate_execution_transition(ExecutionStatus.CREATED, ExecutionStatus.PLANNING)
            ex = ex.model_copy(update={"status": ExecutionStatus.PLANNING, "updated_at": now})
            ex = _append_timeline(ex, "execution_status", {"status": ExecutionStatus.PLANNING.value}, now)
            self._repo.update_execution(ex)

        plan: ExecutionPlan | None = None
        if ex.status == ExecutionStatus.PLANNING:
            plan = self._planner.create_plan(ex, now=now)
            self._repo.save_plan(plan)
            for step in self._instantiate_steps(plan, ex, now):
                self._repo.save_step(step)
            validate_execution_transition(ExecutionStatus.PLANNING, ExecutionStatus.EXECUTING)
            ex = ex.model_copy(
                update={
                    "current_plan_id": plan.plan_id,
                    "status": ExecutionStatus.EXECUTING,
                    "updated_at": now,
                }
            )
            ex = _append_timeline(
                ex,
                "execution_status",
                {"status": ExecutionStatus.EXECUTING.value, "plan_id": str(plan.plan_id)},
                now,
            )
            self._repo.update_execution(ex)

        while True:
            ex = self._repo.get_execution(execution_id)
            assert ex is not None
            if is_execution_terminal(ex.status):
                return ex

            steps = self._repo.list_steps_for_execution(execution_id)
            plan = self._repo.get_plan(ex.current_plan_id) if ex.current_plan_id else None
            if plan is None:
                raise OrchestrationError("execution has no resolvable plan")

            now = datetime.now(timezone.utc)
            ex = self._maybe_enter_validating(ex, steps, now)
            self._repo.update_execution(ex)

            ex = self._repo.get_execution(execution_id)
            assert ex is not None
            if is_execution_terminal(ex.status):
                return ex

            steps = self._repo.list_steps_for_execution(execution_id)
            ordered = self._steps_in_plan_order(steps, plan)
            next_step = self._next_pending_ready(ordered, steps)

            if next_step is not None:
                self._run_step(next_step, now)
                continue

            if all(s.status == StepStatus.SUCCEEDED for s in steps):
                now = datetime.now(timezone.utc)
                if ex.status == ExecutionStatus.VALIDATING:
                    validate_execution_transition(
                        ExecutionStatus.VALIDATING,
                        ExecutionStatus.COMPLETED,
                    )
                    validation_summary = self._validation_summary_from_steps(steps)
                    ex = ex.model_copy(
                        update={
                            "status": ExecutionStatus.COMPLETED,
                            "updated_at": now,
                            "completed_at": now,
                            "validation_summary": validation_summary,
                            "result": {
                                "outcome": "success",
                                "steps": len(steps),
                            },
                        }
                    )
                    ex = _append_timeline(
                        ex,
                        "execution_status",
                        {"status": ExecutionStatus.COMPLETED.value},
                        now,
                    )
                    self._repo.update_execution(ex)
                    return ex

                if ex.status == ExecutionStatus.EXECUTING:
                    raise OrchestrationError(
                        "invariant violated: all steps succeeded but execution not in VALIDATING "
                        "(validation phase required before completion per constitution §6.1)",
                    )

            pending = [s for s in steps if s.status == StepStatus.PENDING]
            if pending:
                raise OrchestrationError("deadlock: pending steps but none are ready")

            raise OrchestrationError("unexpected step set state")

    def _steps_in_plan_order(self, steps: list[Step], plan: ExecutionPlan) -> list[Step]:
        by_key: dict[str, Step] = {}
        for s in steps:
            k = s.input.get("planner_step_key")
            if isinstance(k, str):
                by_key[k] = s
        ordered: list[Step] = []
        for spec in plan.steps:
            key = spec.get("step_key")
            if isinstance(key, str) and key in by_key:
                ordered.append(by_key[key])
        return ordered

    def _next_pending_ready(self, ordered: list[Step], all_steps: list[Step]) -> Step | None:
        """One step per iteration — sequential progress (constitution §2.1)."""
        for s in ordered:
            if s.status == StepStatus.PENDING and self._is_ready(s, all_steps):
                return s
        return None

    def _instantiate_steps(self, plan: ExecutionPlan, execution: Execution, now: datetime) -> list[Step]:
        key_to_id: dict[str, UUID] = {spec["step_key"]: uuid4() for spec in plan.steps}

        built: list[Step] = []
        for spec in plan.steps:
            key = spec["step_key"]
            sid = key_to_id[key]
            deps: list[StepDependency] = []
            for edge in plan.dependencies:
                if edge["to_step"] == key:
                    deps.append(StepDependency(step_id=key_to_id[edge["from_step"]]))
            kind = spec["kind"]
            st_type: StepType | str
            if kind == "validation":
                st_type = StepType.VALIDATION
            elif kind == "reasoning":
                st_type = StepType.REASONING
            else:
                st_type = kind
            agent = spec.get("agent") or self._settings.default_agent_reasoning
            if kind == "validation":
                agent = spec.get("agent") or self._settings.default_agent_validation
            built.append(
                Step(
                    step_id=sid,
                    execution_id=execution.execution_id,
                    plan_id=plan.plan_id,
                    step_type=st_type,
                    agent=agent,
                    input={
                        "planner_step_key": key,
                        "execution_input": execution.input,
                    },
                    status=StepStatus.PENDING,
                    dependencies=deps,
                    retry_count=0,
                    degraded_allowed=bool(spec.get("degraded_allowed", False)),
                    created_at=now,
                    updated_at=now,
                )
            )
        return built

    def _is_ready(self, step: Step, all_steps: list[Step]) -> bool:
        by_id = {s.step_id: s for s in all_steps}
        for dep in step.dependencies:
            parent = by_id.get(dep.step_id)
            if parent is None or parent.status != StepStatus.SUCCEEDED:
                return False
        return True

    def _maybe_enter_validating(self, ex: Execution, steps: list[Step], now: datetime) -> Execution:
        if ex.status != ExecutionStatus.EXECUTING:
            return ex
        if not any(self._is_validation_step(s) for s in steps):
            return ex
        non_val = [s for s in steps if not self._is_validation_step(s)]
        val_steps = [s for s in steps if self._is_validation_step(s)]
        if not val_steps or not non_val:
            return ex
        if all(s.status == StepStatus.SUCCEEDED for s in non_val) and any(
            s.status == StepStatus.PENDING for s in val_steps
        ):
            validate_execution_transition(ExecutionStatus.EXECUTING, ExecutionStatus.VALIDATING)
            ex = ex.model_copy(update={"status": ExecutionStatus.VALIDATING, "updated_at": now})
            return _append_timeline(
                ex,
                "execution_status",
                {"status": ExecutionStatus.VALIDATING.value},
                now,
            )
        return ex

    @staticmethod
    def _is_validation_step(step: Step) -> bool:
        k = step.step_type
        if isinstance(k, StepType):
            return k == StepType.VALIDATION
        return str(k).lower() == "validation"

    def _run_step(self, step: Step, now: datetime) -> None:
        fresh = self._repo.get_step(step.step_id)
        if fresh is None:
            raise OrchestrationError(f"missing step {step.step_id}")
        step = fresh
        validate_step_transition(step.status, StepStatus.RUNNING)
        running = step.model_copy(update={"status": StepStatus.RUNNING, "updated_at": now})
        self._repo.update_step(running)
        ex = self._repo.get_execution(step.execution_id)
        if ex:
            ex = _append_timeline(
                ex,
                "step_status",
                {"step_id": str(step.step_id), "status": StepStatus.RUNNING.value},
                now,
            )
            self._repo.update_execution(ex)

        result = self._executor.execute_step(running)
        self._repo.save_step_result(result)
        validate_step_transition(StepStatus.RUNNING, StepStatus.SUCCEEDED)
        done = running.model_copy(update={"status": StepStatus.SUCCEEDED, "updated_at": now})
        self._repo.update_step(done)

        ex2 = self._repo.get_execution(step.execution_id)
        if ex2:
            ex2 = _append_timeline(
                ex2,
                "step_status",
                {"step_id": str(step.step_id), "status": StepStatus.SUCCEEDED.value},
                now,
            )
            self._repo.update_execution(ex2)

    def _validation_summary_from_steps(self, steps: list[Step]) -> dict[str, Any]:
        for s in steps:
            if not self._is_validation_step(s):
                continue
            res = self._repo.get_step_result(s.step_id)
            if res is None:
                return {"recorded": False, "reason": "missing_step_result"}
            if res.validation_outcome is None:
                return {"recorded": True, "validation_outcome": None}
            return {
                "recorded": True,
                "validation_outcome": res.validation_outcome.model_dump(),
            }
        return {"recorded": False, "reason": "no_validation_step"}


def fail_execution(
    repo: Repository,
    execution_id: UUID,
    *,
    reason: str,
    now: datetime | None = None,
) -> Execution:
    """Move execution to FAILED with explicit reason (constitution §4.2)."""
    ts = now or datetime.now(timezone.utc)
    ex = repo.get_execution(execution_id)
    if ex is None:
        raise KeyError(execution_id)
    if is_execution_terminal(ex.status):
        return ex
    try:
        validate_execution_transition(ex.status, ExecutionStatus.FAILED)
    except InvalidStatusTransitionError:
        return ex
    updated = ex.model_copy(
        update={
            "status": ExecutionStatus.FAILED,
            "updated_at": ts,
            "result": {"outcome": "failed", "reason": reason},
        }
    )
    updated = _append_timeline(
        updated,
        "execution_status",
        {"status": ExecutionStatus.FAILED.value, "reason": reason},
        ts,
    )
    repo.update_execution(updated)
    return updated
