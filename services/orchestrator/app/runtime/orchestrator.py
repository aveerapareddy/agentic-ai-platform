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
    CostAttributionAnalysisModelRequest,
    CostAttributionReasoningOutput,
    CostAttributionValidationModelRequest,
    CostValidationOutput,
    Execution,
    ExecutionPlan,
    ExecutionStatus,
    IncidentAnalysisModelRequest,
    IncidentAnalysisReasoningOutput,
    IncidentValidationModelRequest,
    IncidentValidationReasoningOutput,
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
    ValidationOutcome,
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
from app.runtime.runtime_meta import is_cancellation_requested
from app.runtime.step_executor import StepExecutor
from knowledge_service.service import KnowledgeService
from model_runtime.service import ModelRuntimeService
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
        model_runtime: ModelRuntimeService | None | object = _DEFAULT_CAPABILITY,
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
        self._model_runtime: ModelRuntimeService | None
        if model_runtime is _DEFAULT_CAPABILITY:
            self._model_runtime = ModelRuntimeService()
        else:
            self._model_runtime = model_runtime  # type: ignore[assignment]

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
            if is_cancellation_requested(ex):
                return cancel_execution(self._repo, execution_id, now=datetime.now(timezone.utc))
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
            elif kind == "tool":
                st_type = StepType.TOOL
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
        wt = step.input.get("workflow_type")
        name = step.input.get("planner_step_name")
        if wt == "incident_triage" and name == "gather_evidence":
            return True
        if wt == "cost_attribution" and name in ("retrieve_cost_evidence", "correlate_usage_patterns"):
            return True
        return False

    def _cancellation_check(self, execution_id: UUID):
        def check() -> bool:
            ex = self._repo.get_execution(execution_id)
            return ex is not None and is_cancellation_requested(ex)

        return check

    def _should_use_model_for_step(self, step: Step) -> bool:
        if self._model_runtime is None:
            return False
        wt = step.input.get("workflow_type")
        name = step.input.get("planner_step_name")
        if wt == "incident_triage":
            return name in ("analyze_incident", "validate_incident")
        if wt == "cost_attribution":
            return name in ("analyze_cost_anomaly", "validate_cost_attribution")
        return False

    def _prior_analyze_and_gather_outputs(self, execution_id: UUID) -> tuple[dict[str, Any], dict[str, Any]]:
        analyze_out: dict[str, Any] = {}
        gather_out: dict[str, Any] = {}
        for s in self._repo.list_steps_for_execution(execution_id):
            pname = s.input.get("planner_step_name")
            res = self._repo.get_step_result(s.step_id)
            out = res.output if res is not None and isinstance(res.output, dict) else {}
            if pname == "analyze_incident":
                analyze_out = dict(out)
            elif pname == "gather_evidence":
                gather_out = dict(out)
        return analyze_out, gather_out

    def _trace_model_reasoning(
        self,
        execution_id: UUID,
        step: Step,
        *,
        path: str,
        task: str,
        now: datetime,
        provider: str | None = None,
        error_class: str | None = None,
        error_message: str | None = None,
        invocation: dict[str, Any] | None = None,
    ) -> None:
        ex = self._repo.get_execution(execution_id)
        if ex is None:
            return
        detail: dict[str, Any] = {
            "step_id": str(step.step_id),
            "planner_step_name": step.input.get("planner_step_name"),
            "path": path,
            "task": task,
        }
        if provider:
            detail["provider"] = provider
        if error_class:
            detail["error_class"] = error_class
        if error_message:
            detail["error_message"] = error_message[:500]
        if invocation:
            detail["invocation"] = invocation
        ex = _append_timeline(ex, "model_reasoning", detail, now)
        self._repo.update_execution(ex)

    def _step_result_from_analyze_model(
        self,
        step: Step,
        now: datetime,
        out: IncidentAnalysisReasoningOutput,
    ) -> StepResult:
        rid: ResultId = uuid4()
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output={
                "incident_summary": out.incident_summary,
                "possible_causes": list(out.possible_causes),
            },
            evidence=[
                {
                    "type": "model_reasoning",
                    "provider": out.provider_label,
                    "invocation_id": out.model_invocation_id,
                    "task": "analyze_incident",
                },
            ],
            errors=[],
            latency_ms=1,
            latency_started_at=now,
            latency_ended_at=now,
            confidence_score=0.86,
            confidence_detail={
                "source": "model_runtime",
                "provider": out.provider_label,
                "task": "analyze_incident",
            },
            completeness=StepCompleteness.FULL,
            validation_outcome=None,
            created_at=now,
            updated_at=now,
        )

    def _step_result_from_validate_model(
        self,
        step: Step,
        now: datetime,
        out: IncidentValidationReasoningOutput,
    ) -> StepResult:
        rid: ResultId = uuid4()
        vo = ValidationOutcome(
            status=out.validation_status,
            details={
                "likely_cause": out.likely_cause,
                "model_invocation_id": out.model_invocation_id,
                "provider": out.provider_label,
                "rationale_short": out.rationale_short,
            },
        )
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output={
                "likely_cause": out.likely_cause,
                "validation_status": out.validation_status,
                "confidence_score": out.confidence_score,
                "digest": out.digest,
            },
            evidence=[
                {
                    "type": "model_reasoning",
                    "provider": out.provider_label,
                    "invocation_id": out.model_invocation_id,
                    "task": "validate_incident",
                },
            ],
            errors=[],
            latency_ms=1,
            latency_started_at=now,
            latency_ended_at=now,
            confidence_score=out.confidence_score,
            confidence_detail={
                "source": "model_runtime",
                "provider": out.provider_label,
                "task": "validate_incident",
            },
            completeness=StepCompleteness.FULL,
            validation_outcome=vo,
            created_at=now,
            updated_at=now,
        )

    def _incident_model_reasoning_step(self, step: Step, now: datetime) -> StepResult:
        """Bounded model path with deterministic StepExecutor fallback (Phase 5)."""
        assert self._model_runtime is not None
        name = step.input.get("planner_step_name")
        if not isinstance(name, str):
            return self._executor.execute_step(step)
        ex_in = step.input.get("execution_input")
        if not isinstance(ex_in, dict):
            ex_in = {}
        incident_id = str(ex_in.get("incident_id", ex_in.get("id", "unknown")))
        keys = sorted(ex_in.keys())[:12]
        excerpt = {k: ex_in[k] for k in keys}

        try:
            if name == "analyze_incident":
                req = IncidentAnalysisModelRequest(
                    execution_id=step.execution_id,
                    step_id=step.step_id,
                    incident_id=incident_id,
                    execution_input_excerpt=excerpt,
                )
                call = self._model_runtime.analyze_incident(req)
                out = call.output
                inv = out.invocation.model_dump() if out.invocation is not None else None
                self._trace_model_reasoning(
                    step.execution_id,
                    step,
                    path="model_runtime",
                    task="analyze_incident",
                    now=now,
                    provider=out.provider_label,
                    invocation=inv,
                )
                return self._step_result_from_analyze_model(step, now, out)
            if name == "validate_incident":
                analyze_out, gather_out = self._prior_analyze_and_gather_outputs(step.execution_id)
                pc = analyze_out.get("possible_causes")
                prior_causes = [str(x) for x in pc] if isinstance(pc, list) else []
                req = IncidentValidationModelRequest(
                    execution_id=step.execution_id,
                    step_id=step.step_id,
                    incident_id=incident_id,
                    prior_possible_causes=prior_causes[:16],
                    prior_incident_summary_excerpt=str(analyze_out.get("incident_summary", ""))[:2000],
                    evidence_summary_excerpt=str(gather_out.get("evidence_summary", ""))[:2000],
                )
                vcall = self._model_runtime.validate_incident(req)
                vout = vcall.output
                vinv = vout.invocation.model_dump() if vout.invocation is not None else None
                self._trace_model_reasoning(
                    step.execution_id,
                    step,
                    path="model_runtime",
                    task="validate_incident",
                    now=now,
                    provider=vout.provider_label,
                    invocation=vinv,
                )
                return self._step_result_from_validate_model(step, now, vout)
        except Exception as exc:  # noqa: BLE001 — normalize to fallback + trace
            try:
                from observability import emit_event, get_registry

                get_registry().inc(
                    "model_fallback_total",
                    labels={"task": name if name in ("analyze_incident", "validate_incident") else "unknown"},
                )
                emit_event(
                    "model_fallback",
                    execution_id=str(step.execution_id),
                    step_id=str(step.step_id),
                    task=name,
                    error_class=type(exc).__name__,
                )
            except ImportError:
                pass
            self._trace_model_reasoning(
                step.execution_id,
                step,
                path="deterministic_fallback",
                task=name if name in ("analyze_incident", "validate_incident") else "unknown",
                now=now,
                error_class=type(exc).__name__,
                error_message=str(exc),
            )
            return self._executor.execute_step(step)

        return self._executor.execute_step(step)

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
        assert self._tool_runtime is not None
        tool_rt = self._tool_runtime.with_cancel_check(self._cancellation_check(step.execution_id))
        for tool_name in ("incident_metadata_tool", "signal_lookup_tool"):
            t_req = ToolInvokeRequest(
                execution_id=step.execution_id,
                step_id=step.step_id,
                execution_context_id=ctx.context_id,
                tool_name=tool_name,
                input={"incident_id": incident_id},
            )
            tc = tool_rt.invoke(t_req, now=now)
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

    def _scope_id_from_input(self, ex_in: dict[str, Any]) -> str:
        return str(ex_in.get("scope_id") or ex_in.get("billing_scope_id") or ex_in.get("id", "unknown"))

    def _prior_cost_step_outputs(
        self,
        execution_id: UUID,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        analyze_out: dict[str, Any] = {}
        retrieve_out: dict[str, Any] = {}
        correlate_out: dict[str, Any] = {}
        for s in self._repo.list_steps_for_execution(execution_id):
            pname = s.input.get("planner_step_name")
            res = self._repo.get_step_result(s.step_id)
            out = res.output if res is not None and isinstance(res.output, dict) else {}
            if pname == "analyze_cost_anomaly":
                analyze_out = dict(out)
            elif pname == "retrieve_cost_evidence":
                retrieve_out = dict(out)
            elif pname == "correlate_usage_patterns":
                correlate_out = dict(out)
        return analyze_out, retrieve_out, correlate_out

    def _step_result_from_cost_analyze_model(
        self,
        step: Step,
        now: datetime,
        out: CostAttributionReasoningOutput,
    ) -> StepResult:
        rid: ResultId = uuid4()
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output={
                "suspected_service": out.suspected_service,
                "suspected_team": out.suspected_team,
                "anomaly_type": out.anomaly_type,
                "estimated_cost_impact_usd": out.estimated_cost_impact_usd,
                "attribution_summary": out.attribution_summary,
                "optimization_candidates": list(out.optimization_candidates),
                "evidence_references": list(out.evidence_references),
            },
            evidence=[
                {
                    "type": "model_reasoning",
                    "provider": out.provider_label,
                    "invocation_id": out.model_invocation_id,
                    "task": "analyze_cost_anomaly",
                },
            ],
            errors=[],
            latency_ms=1,
            latency_started_at=now,
            latency_ended_at=now,
            confidence_score=0.85,
            confidence_detail={
                "source": "model_runtime",
                "provider": out.provider_label,
                "task": "analyze_cost_anomaly",
            },
            completeness=StepCompleteness.FULL,
            validation_outcome=None,
            created_at=now,
            updated_at=now,
        )

    def _step_result_from_cost_validate_model(
        self,
        step: Step,
        now: datetime,
        out: CostValidationOutput,
    ) -> StepResult:
        rid: ResultId = uuid4()
        vo = ValidationOutcome(
            status=out.validation_status,
            details={
                "likely_service": out.likely_service,
                "likely_team": out.likely_team,
                "confidence": out.confidence,
                "model_invocation_id": out.model_invocation_id,
                "provider": out.provider_label,
            },
        )
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output={
                "validation_status": out.validation_status,
                "confidence": out.confidence,
                "likely_service": out.likely_service,
                "likely_team": out.likely_team,
                "recommended_actions": list(out.recommended_actions),
                "digest": out.digest,
            },
            evidence=[
                {
                    "type": "model_reasoning",
                    "provider": out.provider_label,
                    "invocation_id": out.model_invocation_id,
                    "task": "validate_cost_attribution",
                },
            ],
            errors=[],
            latency_ms=1,
            latency_started_at=now,
            latency_ended_at=now,
            confidence_score=out.confidence,
            confidence_detail={
                "source": "model_runtime",
                "provider": out.provider_label,
                "task": "validate_cost_attribution",
            },
            completeness=StepCompleteness.FULL,
            validation_outcome=vo,
            created_at=now,
            updated_at=now,
        )

    def _cost_model_reasoning_step(self, step: Step, now: datetime) -> StepResult:
        assert self._model_runtime is not None
        name = step.input.get("planner_step_name")
        if not isinstance(name, str):
            return self._executor.execute_step(step)
        ex_in = step.input.get("execution_input")
        if not isinstance(ex_in, dict):
            ex_in = {}
        scope_id = self._scope_id_from_input(ex_in)
        keys = sorted(ex_in.keys())[:12]
        excerpt = {k: ex_in[k] for k in keys}
        cost_tasks = ("analyze_cost_anomaly", "validate_cost_attribution")

        try:
            if name == "analyze_cost_anomaly":
                req = CostAttributionAnalysisModelRequest(
                    execution_id=step.execution_id,
                    step_id=step.step_id,
                    scope_id=scope_id,
                    execution_input_excerpt=excerpt,
                )
                call = self._model_runtime.analyze_cost_anomaly(req)
                out = call.output
                inv = out.invocation.model_dump() if out.invocation is not None else None
                self._trace_model_reasoning(
                    step.execution_id,
                    step,
                    path="model_runtime",
                    task="analyze_cost_anomaly",
                    now=now,
                    provider=out.provider_label,
                    invocation=inv,
                )
                return self._step_result_from_cost_analyze_model(step, now, out)
            if name == "validate_cost_attribution":
                analyze_out, retrieve_out, correlate_out = self._prior_cost_step_outputs(step.execution_id)
                opt = analyze_out.get("optimization_candidates")
                prior_opt = [str(x) for x in opt] if isinstance(opt, list) else []
                req = CostAttributionValidationModelRequest(
                    execution_id=step.execution_id,
                    step_id=step.step_id,
                    scope_id=scope_id,
                    prior_attribution_summary=str(analyze_out.get("attribution_summary", ""))[:2000],
                    prior_evidence_summary=str(retrieve_out.get("evidence_summary", ""))[:2000],
                    prior_optimization_candidates=prior_opt[:16],
                )
                _ = correlate_out  # correlated signals available for future model prompts
                vcall = self._model_runtime.validate_cost_attribution(req)
                vout = vcall.output
                vinv = vout.invocation.model_dump() if vout.invocation is not None else None
                self._trace_model_reasoning(
                    step.execution_id,
                    step,
                    path="model_runtime",
                    task="validate_cost_attribution",
                    now=now,
                    provider=vout.provider_label,
                    invocation=vinv,
                )
                return self._step_result_from_cost_validate_model(step, now, vout)
        except Exception as exc:  # noqa: BLE001
            try:
                from observability import emit_event, get_registry

                get_registry().inc(
                    "model_fallback_total",
                    labels={"task": name if name in cost_tasks else "unknown"},
                )
                emit_event(
                    "model_fallback",
                    execution_id=str(step.execution_id),
                    step_id=str(step.step_id),
                    task=name,
                    error_class=type(exc).__name__,
                )
            except ImportError:
                pass
            self._trace_model_reasoning(
                step.execution_id,
                step,
                path="deterministic_fallback",
                task=name if name in cost_tasks else "unknown",
                now=now,
                error_class=type(exc).__name__,
                error_message=str(exc),
            )
            return self._executor.execute_step(step)

        return self._executor.execute_step(step)

    def _retrieve_cost_evidence_via_services(self, step: Step, now: datetime) -> StepResult:
        assert self._knowledge is not None
        ex = self._repo.get_execution(step.execution_id)
        if ex is None:
            raise OrchestrationError(f"missing execution {step.execution_id}")
        ctx = self._repo.get_context(ex.execution_context_id)
        if ctx is None:
            raise OrchestrationError(f"missing context {ex.execution_context_id}")
        ex_in = step.input.get("execution_input")
        if not isinstance(ex_in, dict):
            ex_in = {}
        scope_id = self._scope_id_from_input(ex_in)
        service = str(ex_in.get("service_id") or ex_in.get("service") or "")

        filters: dict[str, Any] = {"workflow": "cost_attribution"}
        if service:
            filters["service"] = service

        ret_req = RetrievalRequest(
            tenant_id=ctx.tenant_id,
            workflow_type="cost_attribution",
            query=f"cost billing spend anomaly attribution usage metrics for scope {scope_id}",
            max_results=5,
            filters=filters,
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
                    "workflow_type": "cost_attribution",
                },
                now,
            )
            self._repo.update_execution(ex_cur)

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
                    "document_id": ch.document_id,
                    "source_uri": ch.source_uri,
                    "title": ch.title,
                    "excerpt": ch.text_excerpt[:280],
                    "score": ch.score,
                    "metadata": dict(ch.metadata),
                },
            )

        rid: ResultId = uuid4()
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output={
                "scope_id": scope_id,
                "evidence_summary": (
                    f"Retrieved {len(retrieval.chunks)} cost/billing knowledge chunk(s) for {scope_id}"
                ),
                "chunk_ids": [c.chunk_id for c in retrieval.chunks],
                "retrieval_id": str(retrieval.retrieval_id),
                "corpus_version": retrieval.corpus_version,
            },
            evidence=evidence,
            errors=[],
            latency_ms=1,
            latency_started_at=now,
            latency_ended_at=now,
            confidence_score=0.87,
            confidence_detail={
                "source": "retrieve_cost_evidence",
                "retrieval_id": str(retrieval.retrieval_id),
            },
            completeness=StepCompleteness.FULL,
            validation_outcome=None,
            created_at=now,
            updated_at=now,
        )

    def _correlate_usage_via_tools(self, step: Step, now: datetime) -> StepResult:
        assert self._tool_runtime is not None
        ex = self._repo.get_execution(step.execution_id)
        if ex is None:
            raise OrchestrationError(f"missing execution {step.execution_id}")
        ctx = self._repo.get_context(ex.execution_context_id)
        if ctx is None:
            raise OrchestrationError(f"missing context {ex.execution_context_id}")
        ex_in = step.input.get("execution_input")
        if not isinstance(ex_in, dict):
            ex_in = {}
        scope_id = self._scope_id_from_input(ex_in)
        service = str(ex_in.get("service_id") or ex_in.get("service") or "")

        tool_calls: list[ToolCall] = []
        tool_rt = self._tool_runtime.with_cancel_check(self._cancellation_check(step.execution_id))
        tool_input: dict[str, Any] = {"scope_id": scope_id}
        if service:
            tool_input["service"] = service
        for tool_name in ("cloud_cost_tool", "metrics_lookup_tool"):
            t_req = ToolInvokeRequest(
                execution_id=step.execution_id,
                step_id=step.step_id,
                execution_context_id=ctx.context_id,
                tool_name=tool_name,
                input=dict(tool_input),
            )
            tc = tool_rt.invoke(t_req, now=now)
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
                        "workflow_type": "cost_attribution",
                    },
                    now,
                )
                self._repo.update_execution(ex_t)

        by_name = {tc.tool_name: tc for tc in tool_calls}
        cost_tc = by_name.get("cloud_cost_tool")
        metrics_tc = by_name.get("metrics_lookup_tool")
        cost_out = cost_tc.output if cost_tc and isinstance(cost_tc.output, dict) else {}
        metrics_out = metrics_tc.output if metrics_tc and isinstance(metrics_tc.output, dict) else {}
        signals: list[dict[str, Any]] = []
        raw_sig = metrics_out.get("signals")
        if isinstance(raw_sig, list):
            signals = [dict(x) for x in raw_sig if isinstance(x, dict)]

        evidence: list[dict[str, Any]] = []
        for tc in tool_calls:
            evidence.append(
                {
                    "type": "tool_invocation",
                    "tool_call_id": str(tc.tool_call_id),
                    "tool_name": tc.tool_name,
                    "status": tc.status.value,
                },
            )

        summary_bits = [f"Correlated cost and usage for scope {scope_id}"]
        if cost_out.get("daily_cost_usd") is not None:
            summary_bits.append(f"daily_cost_usd={cost_out.get('daily_cost_usd')}")
        if signals:
            summary_bits.append(f"{len(signals)} usage signal(s)")

        rid: ResultId = uuid4()
        return StepResult(
            step_result_id=rid,
            step_id=step.step_id,
            output={
                "scope_id": scope_id,
                "correlation_summary": "; ".join(summary_bits),
                "tool_call_ids": [str(tc.tool_call_id) for tc in tool_calls],
                "cost_snapshot": dict(cost_out),
                "usage_signals": signals,
            },
            evidence=evidence,
            errors=[],
            latency_ms=1,
            latency_started_at=now,
            latency_ended_at=now,
            confidence_score=0.86,
            confidence_detail={
                "source": "correlate_usage_patterns",
                "tools": [tc.tool_name for tc in tool_calls],
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
            step_name = running.input.get("planner_step_name")
            if running.input.get("workflow_type") == "cost_attribution":
                if step_name == "retrieve_cost_evidence":
                    result = self._retrieve_cost_evidence_via_services(running, now)
                else:
                    result = self._correlate_usage_via_tools(running, now)
            else:
                result = self._gather_evidence_via_services(running, now)
        elif self._should_use_model_for_step(running):
            if running.input.get("workflow_type") == "cost_attribution":
                result = self._cost_model_reasoning_step(running, now)
            else:
                result = self._incident_model_reasoning_step(running, now)
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
        if execution.workflow_type not in ("incident_triage", "cost_attribution"):
            return {"outcome": "success", "steps": len(steps)}
        by_name: dict[str, dict[str, Any]] = {}
        for s in steps:
            name = s.input.get("planner_step_name")
            if not isinstance(name, str):
                continue
            res = self._repo.get_step_result(s.step_id)
            if res is not None and isinstance(res.output, dict):
                by_name[name] = dict(res.output)
        if execution.workflow_type == "cost_attribution":
            analyze = by_name.get("analyze_cost_anomaly", {})
            retrieve = by_name.get("retrieve_cost_evidence", {})
            correlate = by_name.get("correlate_usage_patterns", {})
            validate = by_name.get("validate_cost_attribution", {})
            conf = validate.get("confidence")
            conf_f = float(conf) if isinstance(conf, (int, float)) else None
            return {
                "outcome": "success",
                "workflow_type": "cost_attribution",
                "suspected_service": analyze.get("suspected_service"),
                "suspected_team": analyze.get("suspected_team"),
                "anomaly_type": analyze.get("anomaly_type"),
                "estimated_cost_impact_usd": analyze.get("estimated_cost_impact_usd"),
                "attribution_summary": analyze.get("attribution_summary"),
                "evidence_summary": retrieve.get("evidence_summary"),
                "correlation_summary": correlate.get("correlation_summary"),
                "validation_status": validate.get("validation_status"),
                "confidence": conf_f,
                "likely_service": validate.get("likely_service"),
                "recommended_actions": validate.get("recommended_actions"),
                "optimization_candidates": analyze.get("optimization_candidates"),
                "steps": len(steps),
            }

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


def cancel_execution(
    repo: Repository,
    execution_id: UUID,
    *,
    reason: str = "cancellation_requested",
    now: datetime | None = None,
) -> Execution:
    """Move execution to CANCELLED when transition is allowed (Session C foundation)."""
    from app.runtime.runtime_meta import request_cancellation_meta

    ts = now or datetime.now(timezone.utc)
    ex = repo.get_execution(execution_id)
    if ex is None:
        raise KeyError(execution_id)
    ex = request_cancellation_meta(ex, at=ts, reason=reason)
    if is_execution_terminal(ex.status):
        repo.update_execution(ex)
        return ex
    try:
        validate_execution_transition(ex.status, ExecutionStatus.CANCELLED)
    except InvalidStatusTransitionError:
        repo.update_execution(ex)
        return ex
    updated = ex.model_copy(
        update={
            "status": ExecutionStatus.CANCELLED,
            "updated_at": ts,
            "cancelled_at": ts,
            "result": {"outcome": "cancelled", "reason": reason},
        },
    )
    updated = _append_timeline(
        updated,
        "execution_status",
        {"status": ExecutionStatus.CANCELLED.value, "reason": reason},
        ts,
    )
    repo.update_execution(updated)
    try:
        from observability import emit_event, get_registry

        get_registry().inc("execution_cancellations_total")
        emit_event("execution_cancelled", execution_id=str(execution_id), reason=reason)
    except ImportError:
        pass
    return updated


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
