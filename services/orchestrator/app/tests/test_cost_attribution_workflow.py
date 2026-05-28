"""Session D: cost_attribution workflow — planner, services path, validation lifecycle."""

from __future__ import annotations

from common_schemas import ExecutionStatus

from app.adapters.repository import InMemoryRepository
from app.runtime.orchestrator import ExecutionEngine
from app.services.execution_service import ExecutionService
from model_runtime.service import ModelRuntimeService


def test_cost_attribution_completes_with_model_and_services() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)
    ex = svc.create_execution(
        workflow_type="cost_attribution",
        input_payload={"scope_id": "billing-acme-q2", "service_id": "payments-api"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    assert done.result is not None
    assert done.result.get("workflow_type") == "cost_attribution"
    assert done.result.get("suspected_service") is not None
    assert done.result.get("validation_status") == "passed"

    steps = repo.list_steps_for_execution(ex.execution_id)
    assert len(steps) == 4
    names = {s.input.get("planner_step_name") for s in steps}
    assert names == {
        "analyze_cost_anomaly",
        "retrieve_cost_evidence",
        "correlate_usage_patterns",
        "validate_cost_attribution",
    }

    retrieval_events = [e for e in done.trace_timeline if e.get("event_type") == "knowledge_retrieved"]
    tool_events = [e for e in done.trace_timeline if e.get("event_type") == "tool_call_completed"]
    assert retrieval_events
    assert len(tool_events) >= 2
    model_events = [
        e
        for e in done.trace_timeline
        if e.get("event_type") == "model_reasoning" and e.get("path") == "model_runtime"
    ]
    tasks = {e.get("task") for e in model_events}
    assert "analyze_cost_anomaly" in tasks
    assert "validate_cost_attribution" in tasks


def test_cost_attribution_fallback_when_model_disabled() -> None:
    repo = InMemoryRepository()
    engine = ExecutionEngine(
        repo,
        model_runtime=None,
        tool_runtime=None,
        knowledge_service=None,
    )
    svc = ExecutionService(repo, engine=engine)
    ex = svc.create_execution(
        workflow_type="cost_attribution",
        input_payload={"scope_id": "scope-fb"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    analyze = next(
        s for s in repo.list_steps_for_execution(ex.execution_id)
        if s.input.get("planner_step_name") == "analyze_cost_anomaly"
    )
    ar = repo.get_step_result(analyze.step_id)
    assert ar is not None
    assert (ar.confidence_detail or {}).get("source") == "step_executor_cost_attribution"


def test_cost_model_failure_triggers_fallback() -> None:
    class Boom:
        def analyze_cost_anomaly(self, request):  # noqa: ANN001
            raise RuntimeError("simulated cost model failure")

        def validate_cost_attribution(self, request):  # noqa: ANN001
            raise RuntimeError("simulated cost model failure")

        def analyze_incident(self, request):  # noqa: ANN001
            raise RuntimeError("not used")

        def validate_incident(self, request):  # noqa: ANN001
            raise RuntimeError("not used")

    repo = InMemoryRepository()
    engine = ExecutionEngine(repo, model_runtime=ModelRuntimeService(client=Boom()))  # type: ignore[arg-type]
    svc = ExecutionService(repo, engine=engine)
    ex = svc.create_execution(
        workflow_type="cost_attribution",
        input_payload={"scope_id": "scope-boom"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    fallbacks = [
        e
        for e in done.trace_timeline
        if e.get("event_type") == "model_reasoning" and e.get("path") == "deterministic_fallback"
    ]
    assert fallbacks
