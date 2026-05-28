"""Delegate execution, trace, approval, and replay to orchestrator ports — no workflow logic."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from gateway._bootstrap import ensure_platform_paths
from gateway.config import Settings

ensure_platform_paths()

from app.adapters.repository import Repository
from app.runtime.orchestrator import OrchestrationError
from app.services.execution_service import ExecutionService
from app.services.replay_service import ReplayNotFoundError, ReplayService, ReplayValidationError
from common_schemas import (
    ApprovalDecision,
    Execution,
    ExecutionContext,
    ExecutionMode,
    ExecutionStatus,
    ReplayCreatedResponse,
    ReplayMode,
    ReplayRequest,
)
from common_schemas.policy import Approval
from common_schemas.tooling import ToolCall
from common_schemas.workflow import ExecutionPlan


REGISTERED_WORKFLOW_TYPES = frozenset({"incident_triage", "generic"})


def _dump_model(m: Any) -> dict[str, Any]:
    if hasattr(m, "model_dump"):
        return m.model_dump(mode="json")
    return dict(m)


class ExecutionFacade:
    def __init__(
        self,
        *,
        execution_service: ExecutionService,
        repository: Repository,
        idempotency_store: dict[tuple[str, str, str], UUID],
        settings: Settings,
        replay_service: ReplayService | None = None,
    ) -> None:
        self._svc = execution_service
        self._repo = repository
        self._idem = idempotency_store
        self._settings = settings
        self._replay = replay_service or ReplayService(repository, execution_service)

    def create_execution(
        self,
        *,
        workflow_type: str,
        input_payload: dict[str, Any],
        context: dict[str, Any],
        idempotency_key: str | None,
        schedule_start: bool | None = None,
        start_callback: Any | None = None,
    ) -> Execution:
        if workflow_type not in REGISTERED_WORKFLOW_TYPES:
            msg = f"unsupported workflow_type (registered: {sorted(REGISTERED_WORKFLOW_TYPES)})"
            raise ValueError(msg)
        tenant_id = context.get("tenant_id")
        policy_scope = context.get("policy_scope")
        if not tenant_id or not policy_scope:
            raise ValueError("context.tenant_id and context.policy_scope are required")
        request_id = context.get("request_id") or "gateway"
        environment = context.get("environment") or "dev"
        principal_id = context.get("principal_id")
        permissions_scope = context.get("permissions_scope")
        feature_flags = context.get("feature_flags")
        mode_raw = context.get("execution_mode")
        execution_mode = ExecutionMode.BACKGROUND
        if mode_raw is not None:
            try:
                execution_mode = ExecutionMode(str(mode_raw))
            except ValueError:
                raise ValueError("execution_mode must be interactive or background") from None

        if idempotency_key:
            key = (str(tenant_id), workflow_type, idempotency_key)
            if key in self._idem:
                existing = self._repo.get_execution(self._idem[key])
                if existing is not None:
                    return existing

        ex = self._svc.create_execution(
            workflow_type=workflow_type,
            input_payload=input_payload,
            tenant_id=str(tenant_id),
            request_id=str(request_id),
            environment=str(environment),
            policy_scope=str(policy_scope),
            principal_id=str(principal_id) if principal_id else None,
            execution_mode=execution_mode,
            permissions_scope=permissions_scope if isinstance(permissions_scope, dict) else None,
            feature_flags=feature_flags if isinstance(feature_flags, dict) else None,
        )

        if idempotency_key:
            self._idem[(str(tenant_id), workflow_type, idempotency_key)] = ex.execution_id

        do_start = self._settings.schedule_execution_start if schedule_start is None else schedule_start
        if do_start:
            if self._settings.use_execution_worker_queue and execution_mode == ExecutionMode.BACKGROUND:
                self._svc.enqueue_execution(ex.execution_id)
            elif start_callback is not None:
                start_callback(ex.execution_id)
            else:
                self._svc.start_execution(ex.execution_id)

        return ex

    def request_cancellation(self, execution_id: UUID, *, reason: str = "operator") -> Execution:
        return self._svc.request_cancellation(execution_id, reason=reason)

    def get_execution(self, execution_id: UUID) -> Execution | None:
        return self._svc.get_execution(execution_id)

    def list_executions(
        self,
        *,
        tenant_id: str | None,
        workflow_type: str | None,
        status: str | None,
        limit: int,
    ) -> list[Execution]:
        st: ExecutionStatus | str | None = status
        if status is not None:
            try:
                st = ExecutionStatus(status)
            except ValueError:
                st = status
        return self._svc.list_executions(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=st,
            limit=limit,
        )

    def build_trace_projection(self, execution_id: UUID) -> dict[str, Any] | None:
        ex = self._repo.get_execution(execution_id)
        if ex is None:
            return None
        ctx = self._repo.get_context(ex.execution_context_id)
        if ctx is None:
            return None

        steps = self._repo.list_steps_for_execution(execution_id)
        plan_ids = {s.plan_id for s in steps}
        plans: list[ExecutionPlan] = []
        for pid in sorted(plan_ids, key=lambda x: str(x)):
            p = self._repo.get_plan(pid)
            if p is not None:
                plans.append(p)

        step_payloads: list[dict[str, Any]] = []
        tool_calls_flat: list[ToolCall] = []
        for s in steps:
            sr = self._repo.get_step_result(s.step_id)
            step_payloads.append(
                {
                    "step": _dump_model(s),
                    "step_result": _dump_model(sr) if sr is not None else None,
                }
            )
            for tc in self._repo.list_tool_calls_for_step(s.step_id):
                tool_calls_flat.append(tc)

        evals = self._repo.list_policy_evaluations_for_execution(execution_id)
        approvals = self._repo.list_approvals_for_execution(execution_id)

        return {
            "execution_id": str(execution_id),
            "execution_context": _dump_model(ctx),
            "plans": [_dump_model(p) for p in plans],
            "steps": step_payloads,
            "tool_calls": [_dump_model(tc) for tc in tool_calls_flat],
            "policy_evaluations": [_dump_model(e) for e in evals],
            "approvals": [_dump_model(a) for a in approvals],
            "timeline": list(ex.trace_timeline),
        }

    def submit_approval(
        self,
        execution_id: UUID,
        *,
        action_proposal_id: UUID | None,
        policy_evaluation_id: UUID | None,
        decision: str,
        approver: str,
        notes: str | None,
    ) -> Approval:
        if action_proposal_id is None and policy_evaluation_id is None:
            raise ValueError("at least one of action_proposal_id or policy_evaluation_id is required")
        try:
            ad = ApprovalDecision(decision)
        except ValueError as e:
            raise ValueError(f"invalid decision: {decision}") from e

        ex = self._repo.get_execution(execution_id)
        if ex is None:
            raise KeyError(execution_id)
        if ex.status == ExecutionStatus.AWAITING_APPROVAL and isinstance(ex.result, dict):
            gov = ex.result.get("governance")
            if isinstance(gov, dict) and action_proposal_id is not None and policy_evaluation_id is not None:
                if str(action_proposal_id) != str(gov.get("proposal_id")):
                    raise ValueError("action_proposal_id does not match execution governance snapshot")
                if str(policy_evaluation_id) != str(gov.get("evaluation_id")):
                    raise ValueError("policy_evaluation_id does not match execution governance snapshot")

        try:
            self._svc.submit_approval(execution_id, approver=approver, decision=ad, notes=notes)
        except OrchestrationError:
            raise

        approvals = self._repo.list_approvals_for_execution(execution_id)
        if not approvals:
            raise RuntimeError("approval not persisted")
        return approvals[-1]

    def request_replay(
        self,
        source_execution_id: UUID,
        *,
        mode: str,
        plan_id: UUID | None,
        environment_target: str,
        label: str | None,
        reason: str | None = None,
        requested_by: str | None = None,
        input_overrides: dict[str, Any] | None = None,
        start_execution: bool = False,
    ) -> ReplayCreatedResponse:
        """Delegate to orchestrator ReplayService; does not construct replay in the gateway."""
        try:
            rmode = ReplayMode(mode)
        except ValueError as e:
            raise ValueError(f"invalid replay mode: {mode}") from e

        request = ReplayRequest(
            source_execution_id=source_execution_id,
            replay_mode=rmode,
            environment_target=environment_target,
            anchor_plan_id=plan_id,
            label=label,
            reason=reason,
            requested_by=requested_by,
            input_overrides=input_overrides,
            start_execution=start_execution,
        )
        try:
            return self._replay.create_replay(request)
        except ReplayNotFoundError as e:
            raise KeyError(str(e)) from e
        except ReplayValidationError as e:
            raise ValueError(str(e)) from e
