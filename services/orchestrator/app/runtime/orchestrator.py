"""Execution loop: coordinator only; policy decisions via policy_engine (constitution §3.1, §8.2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from common_schemas import (
    ActionId,
    ActionProposal,
    ActionProposalStatus,
    Approval,
    ApprovalDecision,
    Execution,
    ExecutionPlan,
    ExecutionStatus,
    PolicyDecision,
    PolicyEvaluation,
    PolicyEvaluationId,
    ResultId,
    RetrievalRequest,
    RiskLevel,
    Step,
    StepCompleteness,
    StepDependency,
    StepResult,
    StepStatus,
    StepType,
    ToolCall,
    ToolInvokeRequest,
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
from knowledge_service.service import KnowledgeService
from policy_engine.service import PolicyEvaluationService
from tool_runtime.service import ToolRuntimeService


class OrchestrationError(RuntimeError):
    """Raised when the run cannot make progress (recorded; may lead to FAILED)."""


_DEFAULT_CAPABILITY = object()


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
        policy_service: PolicyEvaluationService | None = None,
        tool_runtime: ToolRuntimeService | None | object = _DEFAULT_CAPABILITY,
        knowledge_service: KnowledgeService | None | object = _DEFAULT_CAPABILITY,
    ) -> None:
        self._repo = repository
        self._planner = planner or Planner()
        self._executor = step_executor or StepExecutor()
        self._settings = settings or OrchestratorSettings()
        self._policy = policy_service or PolicyEvaluationService()
        self._tool_runtime: ToolRuntimeService | None
        if tool_runtime is _DEFAULT_CAPABILITY:
            self._tool_runtime = ToolRuntimeService()
        else:
            self._tool_runtime = tool_runtime  # type: ignore[assignment]
        self._knowledge: KnowledgeService | None
        if knowledge_service is _DEFAULT_CAPABILITY:
            self._knowledge = KnowledgeService()
        else:
            self._knowledge = knowledge_service  # type: ignore[assignment]

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
            if ex.status == ExecutionStatus.AWAITING_APPROVAL:
                return ex
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
                    if ex.workflow_type == "incident_triage":
                        ex = self._finalize_incident_triage_governance(ex, steps, now)
                        self._repo.update_execution(ex)
                        return ex
                    validate_execution_transition(
                        ExecutionStatus.VALIDATING,
                        ExecutionStatus.COMPLETED,
                    )
                    validation_summary = self._validation_summary_from_steps(steps)
                    result_payload = self._build_completion_result(ex, steps)
                    ex = ex.model_copy(
                        update={
                            "status": ExecutionStatus.COMPLETED,
                            "updated_at": now,
                            "completed_at": now,
                            "validation_summary": validation_summary,
                            "result": result_payload,
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
            elif kind == "retrieval":
                st_type = StepType.RETRIEVAL
            else:
                st_type = kind
            agent = spec.get("agent") or self._settings.default_agent_reasoning
            if kind == "validation":
                agent = spec.get("agent") or self._settings.default_agent_validation
            elif kind == "retrieval":
                agent = spec.get("agent") or self._settings.default_agent_retrieval
            step_name = spec.get("step_name")
            built.append(
                Step(
                    step_id=sid,
                    execution_id=execution.execution_id,
                    plan_id=plan.plan_id,
                    step_type=st_type,
                    agent=agent,
                    input={
                        "planner_step_key": key,
                        "planner_step_name": step_name,
                        "workflow_type": execution.workflow_type,
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

    def _should_use_tooling_for_step(self, step: Step) -> bool:
        if self._tool_runtime is None or self._knowledge is None:
            return False
        return (
            step.input.get("workflow_type") == "incident_triage"
            and step.input.get("planner_step_name") == "gather_evidence"
        )

    def _gather_evidence_via_services(self, step: Step, now: datetime) -> StepResult:
        """Coordinator path: knowledge-service + tool-runtime; persists ToolCalls (Phase 4)."""
        assert self._tool_runtime is not None and self._knowledge is not None
        ex = self._repo.get_execution(step.execution_id)
        if ex is None:
            raise OrchestrationError(f"missing execution {step.execution_id}")
        ctx = self._repo.get_context(ex.execution_context_id)
        if ctx is None:
            raise OrchestrationError(f"missing context {ex.execution_context_id}")
        ex_in = step.input.get("execution_input")
        if not isinstance(ex_in, dict):
            ex_in = {}
        incident_id = str(ex_in.get("incident_id", ex_in.get("id", "unknown")))

        ret_req = RetrievalRequest(
            tenant_id=ctx.tenant_id,
            workflow_type="incident_triage",
            query=(
                f"incident triage evidence correlation latency error deploy for incident {incident_id}"
            ),
            max_results=5,
            filters={"incident_id": incident_id},
            correlation_request_id=ctx.request_id,
        )
        retrieval = self._knowledge.retrieve(ret_req)
        ex_cur = self._repo.get_execution(step.execution_id)
        if ex_cur:
            ex_cur = _append_timeline(
                ex_cur,
                "knowledge_retrieved",
                {
                    "step_id": str(step.step_id),
                    "retrieval_id": str(retrieval.retrieval_id),
                    "chunk_count": len(retrieval.chunks),
                    "corpus_version": retrieval.corpus_version,
                },
                now,
            )
            self._repo.update_execution(ex_cur)

        tool_calls: list[ToolCall] = []
        for tool_name in ("incident_metadata_tool", "signal_lookup_tool"):
            t_req = ToolInvokeRequest(
                execution_id=step.execution_id,
                step_id=step.step_id,
                execution_context_id=ctx.context_id,
                tool_name=tool_name,
                input={"incident_id": incident_id},
            )
            tc = self._tool_runtime.invoke(t_req, now=now)
            self._repo.save_tool_call(tc)
            tool_calls.append(tc)
            ex_t = self._repo.get_execution(step.execution_id)
            if ex_t:
                ex_t = _append_timeline(
                    ex_t,
                    "tool_call_completed",
                    {
                        "step_id": str(step.step_id),
                        "tool_call_id": str(tc.tool_call_id),
                        "tool_name": tc.tool_name,
                        "status": tc.status.value,
                        "latency_ms": tc.latency_ms,
                    },
                    now,
                )
                self._repo.update_execution(ex_t)

        by_name = {tc.tool_name: tc for tc in tool_calls}
        meta_tc = by_name.get("incident_metadata_tool")
        sig_tc = by_name.get("signal_lookup_tool")
        meta_out = meta_tc.output if meta_tc and isinstance(meta_tc.output, dict) else {}
        sig_out = sig_tc.output if sig_tc and isinstance(sig_tc.output, dict) else {}
        signals: list[dict[str, Any]] = []
        raw_sig = sig_out.get("signals")
        if isinstance(raw_sig, list):
            signals = [dict(x) for x in raw_sig if isinstance(x, dict)]

        evidence: list[dict[str, Any]] = [
            {
                "type": "knowledge_retrieval",
                "retrieval_id": str(retrieval.retrieval_id),
                "corpus_version": retrieval.corpus_version,
                "chunk_ids": [c.chunk_id for c in retrieval.chunks],
            },
        ]
        for ch in retrieval.chunks:
            evidence.append(
                {
                    "type": "knowledge_chunk",
                    "chunk_id": ch.chunk_id,
                    "source_uri": ch.source_uri,
                    "title": ch.title,
                    "excerpt": ch.text_excerpt[:280],
                    "score": ch.score,
                },
            )
        for tc in tool_calls:
            evidence.append(
                {
                    "type": "tool_invocation",
                    "tool_call_id": str(tc.tool_call_id),
                    "tool_name": tc.tool_name,
                    "status": tc.status.value,
                },
            )

        summary_bits = [
            f"Retrieved {len(retrieval.chunks)} knowledge chunk(s) for {incident_id}",
        ]
        if meta_out.get("service"):
            summary_bits.append(f"metadata service={meta_out.get('service')}")
        if signals:
            summary_bits.append(f"{len(signals)} signal(s) from signal_lookup_tool")

        rid: ResultId = uuid4()
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output={
                "evidence_summary": "; ".join(summary_bits),
                "signals": signals,
                "retrieval_id": str(retrieval.retrieval_id),
                "tool_call_ids": [str(tc.tool_call_id) for tc in tool_calls],
                "incident_id": incident_id,
                "metadata_snapshot": dict(meta_out),
            },
            evidence=evidence,
            errors=[],
            latency_ms=1,
            latency_started_at=now,
            latency_ended_at=now,
            confidence_score=0.88,
            confidence_detail={
                "source": "gather_evidence_phase4",
                "tools": [tc.tool_name for tc in tool_calls],
                "retrieval_id": str(retrieval.retrieval_id),
            },
            completeness=StepCompleteness.FULL,
            validation_outcome=None,
            created_at=now,
            updated_at=now,
        )

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
                "step_started",
                {
                    "step_id": str(step.step_id),
                    "planner_step_name": step.input.get("planner_step_name"),
                    "workflow_type": step.input.get("workflow_type"),
                },
                now,
            )
            self._repo.update_execution(ex)

        if self._should_use_tooling_for_step(running):
            result = self._gather_evidence_via_services(running, now)
        else:
            result = self._executor.execute_step(running)
        self._repo.save_step_result(result)
        validate_step_transition(StepStatus.RUNNING, StepStatus.SUCCEEDED)
        done = running.model_copy(update={"status": StepStatus.SUCCEEDED, "updated_at": now})
        self._repo.update_step(done)

        ex2 = self._repo.get_execution(step.execution_id)
        if ex2:
            ex2 = _append_timeline(
                ex2,
                "step_completed",
                {
                    "step_id": str(step.step_id),
                    "planner_step_name": step.input.get("planner_step_name"),
                    "workflow_type": step.input.get("workflow_type"),
                },
                now,
            )
            if self._is_validation_step(done):
                ex2 = _append_timeline(
                    ex2,
                    "validation_performed",
                    {
                        "step_id": str(step.step_id),
                        "planner_step_name": step.input.get("planner_step_name"),
                        "validation_status": (result.output or {}).get("validation_status")
                        if isinstance(result.output, dict)
                        else None,
                    },
                    now,
                )
            self._repo.update_execution(ex2)

    def _build_completion_result(self, execution: Execution, steps: list[Step]) -> dict[str, Any]:
        """Workflow-specific terminal result; generic workflows keep a minimal success payload."""
        if execution.workflow_type != "incident_triage":
            return {"outcome": "success", "steps": len(steps)}
        by_name: dict[str, dict[str, Any]] = {}
        for s in steps:
            name = s.input.get("planner_step_name")
            if not isinstance(name, str):
                continue
            res = self._repo.get_step_result(s.step_id)
            if res is not None and isinstance(res.output, dict):
                by_name[name] = dict(res.output)
        analyze = by_name.get("analyze_incident", {})
        gather = by_name.get("gather_evidence", {})
        validate = by_name.get("validate_incident", {})
        conf = validate.get("confidence_score")
        conf_f: float | None
        if isinstance(conf, (int, float)):
            conf_f = float(conf)
        else:
            conf_f = None
        return {
            "outcome": "success",
            "workflow_type": "incident_triage",
            "incident_summary": analyze.get("incident_summary"),
            "likely_cause": validate.get("likely_cause"),
            "evidence_summary": gather.get("evidence_summary"),
            "validation_status": validate.get("validation_status"),
            "confidence_score": conf_f,
            "steps": len(steps),
        }

    @staticmethod
    def _step_by_planner_name(steps: list[Step], name: str) -> Step | None:
        for s in steps:
            if s.input.get("planner_step_name") == name:
                return s
        return None

    def _step_output_by_name(self, steps: list[Step], name: str) -> dict[str, Any]:
        s = self._step_by_planner_name(steps, name)
        if s is None:
            return {}
        res = self._repo.get_step_result(s.step_id)
        if res is None or not isinstance(res.output, dict):
            return {}
        return dict(res.output)

    def _finalize_incident_triage_governance(
        self,
        ex: Execution,
        steps: list[Step],
        now: datetime,
    ) -> Execution:
        """After validation steps succeed: propose escalate_incident, evaluate policy, branch."""
        ctx = self._repo.get_context(ex.execution_context_id)
        if ctx is None:
            raise OrchestrationError("missing execution context for governance")

        validation_summary = self._validation_summary_from_steps(steps)
        base_result = self._build_completion_result(ex, steps)
        validate_step = self._step_by_planner_name(steps, "validate_incident")
        validate_sid = validate_step.step_id if validate_step else None
        validate_out = self._step_output_by_name(steps, "validate_incident")

        proposal_id: ActionId = uuid4()
        proposal = ActionProposal(
            proposal_id=proposal_id,
            execution_id=ex.execution_id,
            step_id=validate_sid,
            action_type="escalate_incident",
            payload={
                "incident_id": ex.input.get("incident_id", ex.input.get("id")),
                "likely_cause": validate_out.get("likely_cause"),
                "severity": ex.input.get("severity"),
            },
            risk_level=RiskLevel.HIGH,
            requires_approval=False,
            status=ActionProposalStatus.PROPOSED,
            created_at=now,
            updated_at=now,
        )
        self._repo.save_action_proposal(proposal)
        ex = _append_timeline(
            ex,
            "action_proposed",
            {
                "proposal_id": str(proposal_id),
                "action_type": proposal.action_type,
                "risk_level": proposal.risk_level.value,
            },
            now,
        )

        draft = self._policy.evaluate_proposal(ctx, proposal)
        eval_id: PolicyEvaluationId = uuid4()
        evaluation = PolicyEvaluation(
            evaluation_id=eval_id,
            execution_id=ex.execution_id,
            execution_context_id=ctx.context_id,
            decision=draft.decision,
            reason=draft.reason,
            evaluated_rules=list(draft.evaluated_rules),
            subject_ref={
                "proposal_id": str(proposal_id),
                "action_type": proposal.action_type,
            },
            created_at=now,
            updated_at=now,
        )
        self._repo.save_policy_evaluation(evaluation)
        ex = _append_timeline(
            ex,
            "policy_evaluated",
            {
                "evaluation_id": str(eval_id),
                "decision": draft.decision.value,
                "reason": draft.reason,
            },
            now,
        )

        proposed_action = {
            "type": proposal.action_type,
            "proposal_id": str(proposal_id),
        }

        if draft.decision == PolicyDecision.DENY:
            proposal_done = proposal.model_copy(
                update={"status": ActionProposalStatus.POLICY_DENIED, "updated_at": now}
            )
            self._repo.save_action_proposal(proposal_done)
            validate_execution_transition(ExecutionStatus.VALIDATING, ExecutionStatus.FAILED)
            result = {
                **base_result,
                "outcome": "failed",
                "workflow_type": "incident_triage",
                "proposed_action": proposed_action,
                "policy_decision": PolicyDecision.DENY.value,
                "approval_status": "not_applicable",
            }
            ex = ex.model_copy(
                update={
                    "status": ExecutionStatus.FAILED,
                    "updated_at": now,
                    "validation_summary": validation_summary,
                    "result": result,
                }
            )
            ex = _append_timeline(
                ex,
                "governed_outcome",
                {"path": "policy_denied", "proposal_id": str(proposal_id)},
                now,
            )
            ex = _append_timeline(
                ex,
                "execution_status",
                {"status": ExecutionStatus.FAILED.value},
                now,
            )
            return ex

        if draft.decision == PolicyDecision.ALLOW:
            proposal_done = proposal.model_copy(
                update={"status": ActionProposalStatus.APPROVED, "updated_at": now}
            )
            self._repo.save_action_proposal(proposal_done)
            validate_execution_transition(ExecutionStatus.VALIDATING, ExecutionStatus.COMPLETED)
            result = {
                **base_result,
                "proposed_action": proposed_action,
                "policy_decision": PolicyDecision.ALLOW.value,
                "approval_status": "not_required",
            }
            ex = ex.model_copy(
                update={
                    "status": ExecutionStatus.COMPLETED,
                    "updated_at": now,
                    "completed_at": now,
                    "validation_summary": validation_summary,
                    "result": result,
                }
            )
            ex = _append_timeline(
                ex,
                "governed_outcome",
                {"path": "policy_allow", "proposal_id": str(proposal_id)},
                now,
            )
            ex = _append_timeline(
                ex,
                "execution_status",
                {"status": ExecutionStatus.COMPLETED.value},
                now,
            )
            return ex

        proposal_pending = proposal.model_copy(
            update={
                "status": ActionProposalStatus.AWAITING_APPROVAL,
                "requires_approval": True,
                "updated_at": now,
            }
        )
        self._repo.save_action_proposal(proposal_pending)
        validate_execution_transition(
            ExecutionStatus.VALIDATING,
            ExecutionStatus.AWAITING_APPROVAL,
        )
        result = {
            **base_result,
            "outcome": "awaiting_approval",
            "workflow_type": "incident_triage",
            "governance": {
                "phase": "awaiting_approval",
                "proposal_id": str(proposal_id),
                "evaluation_id": str(eval_id),
                "policy_decision": PolicyDecision.CONDITIONAL.value,
            },
            "proposed_action": proposed_action,
            "policy_decision": PolicyDecision.CONDITIONAL.value,
            "approval_status": "pending",
        }
        ex = ex.model_copy(
            update={
                "status": ExecutionStatus.AWAITING_APPROVAL,
                "updated_at": now,
                "validation_summary": validation_summary,
                "result": result,
            }
        )
        ex = _append_timeline(
            ex,
            "approval_required",
            {
                "proposal_id": str(proposal_id),
                "evaluation_id": str(eval_id),
            },
            now,
        )
        ex = _append_timeline(
            ex,
            "execution_status",
            {"status": ExecutionStatus.AWAITING_APPROVAL.value},
            now,
        )
        return ex

    def submit_approval(
        self,
        execution_id: UUID,
        *,
        approver: str,
        decision: ApprovalDecision,
        notes: str | None = None,
        now: datetime | None = None,
    ) -> Execution:
        """Record human decision for AWAITING_APPROVAL incident triage; complete or fail execution."""
        ts = now or datetime.now(timezone.utc)
        ex = self._repo.get_execution(execution_id)
        if ex is None:
            raise KeyError(execution_id)
        if ex.status != ExecutionStatus.AWAITING_APPROVAL:
            msg = f"execution {execution_id} not awaiting approval (status={ex.status})"
            raise OrchestrationError(msg)
        result = ex.result or {}
        gov = result.get("governance")
        if not isinstance(gov, dict):
            raise OrchestrationError("missing governance block on execution result")
        pid_raw = gov.get("proposal_id")
        eid_raw = gov.get("evaluation_id")
        if not isinstance(pid_raw, str) or not isinstance(eid_raw, str):
            raise OrchestrationError("governance missing proposal_id or evaluation_id")
        proposal_id = UUID(pid_raw)
        evaluation_id = UUID(eid_raw)

        if decision == ApprovalDecision.DEFER:
            raise OrchestrationError("approval defer is not supported in Phase 3")

        approval = Approval(
            approval_id=uuid4(),
            execution_id=ex.execution_id,
            policy_evaluation_id=evaluation_id,
            action_proposal_id=proposal_id,
            approver=approver,
            decision=decision,
            notes=notes,
            decided_at=ts,
            created_at=ts,
            updated_at=ts,
        )
        self._repo.save_approval(approval)
        ex = _append_timeline(
            ex,
            "approval_received",
            {
                "approval_id": str(approval.approval_id),
                "decision": decision.value,
                "approver": approver,
            },
            ts,
        )

        proposal = self._repo.get_action_proposal(proposal_id)
        if proposal is None:
            raise OrchestrationError("action proposal not found")

        steps = self._repo.list_steps_for_execution(execution_id)
        validation_summary = self._validation_summary_from_steps(steps)
        base_result = self._build_completion_result(ex, steps)
        proposed_action = {
            "type": proposal.action_type,
            "proposal_id": str(proposal_id),
        }

        if decision == ApprovalDecision.REJECT:
            prop = proposal.model_copy(update={"status": ActionProposalStatus.REJECTED, "updated_at": ts})
            self._repo.save_action_proposal(prop)
            validate_execution_transition(ExecutionStatus.AWAITING_APPROVAL, ExecutionStatus.FAILED)
            final_result = {
                **base_result,
                "outcome": "failed",
                "workflow_type": "incident_triage",
                "proposed_action": proposed_action,
                "policy_decision": PolicyDecision.CONDITIONAL.value,
                "approval_status": "rejected",
            }
            ex = ex.model_copy(
                update={
                    "status": ExecutionStatus.FAILED,
                    "updated_at": ts,
                    "validation_summary": validation_summary,
                    "result": final_result,
                }
            )
            ex = _append_timeline(
                ex,
                "governed_outcome",
                {"path": "approval_rejected", "proposal_id": str(proposal_id)},
                ts,
            )
            ex = _append_timeline(
                ex,
                "execution_status",
                {"status": ExecutionStatus.FAILED.value},
                ts,
            )
            self._repo.update_execution(ex)
            return ex

        prop = proposal.model_copy(update={"status": ActionProposalStatus.APPROVED, "updated_at": ts})
        self._repo.save_action_proposal(prop)
        validate_execution_transition(ExecutionStatus.AWAITING_APPROVAL, ExecutionStatus.COMPLETED)
        final_result = {
            **base_result,
            "proposed_action": proposed_action,
            "policy_decision": PolicyDecision.CONDITIONAL.value,
            "approval_status": "approved",
        }
        ex = ex.model_copy(
            update={
                "status": ExecutionStatus.COMPLETED,
                "updated_at": ts,
                "completed_at": ts,
                "validation_summary": validation_summary,
                "result": final_result,
            }
        )
        ex = _append_timeline(
            ex,
            "governed_outcome",
            {"path": "approval_granted", "proposal_id": str(proposal_id)},
            ts,
        )
        ex = _append_timeline(
            ex,
            "execution_status",
            {"status": ExecutionStatus.COMPLETED.value},
            ts,
        )
        self._repo.update_execution(ex)
        return ex

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
