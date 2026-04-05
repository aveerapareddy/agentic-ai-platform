"""Phase 5: model-runtime path, fallback, trace, end-to-end."""

from __future__ import annotations

from common_schemas import ExecutionStatus

from app.adapters.repository import InMemoryRepository
from app.runtime.orchestrator import ExecutionEngine
from app.services.execution_service import ExecutionService
from model_runtime.service import ModelRuntimeService


def test_analyze_uses_model_runtime_by_default() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "m1"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    model_events = [
        e
        for e in done.trace_timeline
        if e.get("event_type") == "model_reasoning" and e.get("path") == "model_runtime"
    ]
    tasks = {e.get("task") for e in model_events}
    assert "analyze_incident" in tasks
    assert "validate_incident" in tasks
    steps = repo.list_steps_for_execution(ex.execution_id)
    analyze = next(s for s in steps if s.input.get("planner_step_name") == "analyze_incident")
    ar = repo.get_step_result(analyze.step_id)
    assert ar is not None
    assert ar.output is not None
    summary = str(ar.output.get("incident_summary", ""))
    assert "fake_structured_v1" in summary or "[model:" in summary


def test_model_runtime_disabled_uses_detinistic_fallback() -> None:
    repo = InMemoryRepository()
    engine = ExecutionEngine(
        repo,
        model_runtime=None,
        tool_runtime=None,
        knowledge_service=None,
    )
    svc = ExecutionService(repo, engine=engine)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "fb1"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    assert not any(
        e.get("event_type") == "model_reasoning" and e.get("path") == "model_runtime"
        for e in done.trace_timeline
    )
    steps = repo.list_steps_for_execution(ex.execution_id)
    analyze = next(s for s in steps if s.input.get("planner_step_name") == "analyze_incident")
    ar = repo.get_step_result(analyze.step_id)
    assert ar is not None
    src = (ar.confidence_detail or {}).get("source")
    assert src == "step_executor_incident_triage"


def test_failing_model_client_triggers_fallback_trace() -> None:
    class Boom:
        def analyze_incident(self, request):  # noqa: ANN001
            raise RuntimeError("simulated model failure")

        def validate_incident(self, request):  # noqa: ANN001
            raise RuntimeError("simulated model failure")

    repo = InMemoryRepository()
    engine = ExecutionEngine(repo, model_runtime=ModelRuntimeService(client=Boom()))  # type: ignore[arg-type]
    svc = ExecutionService(repo, engine=engine)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "boom"},
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
    assert len(fallbacks) >= 1
    assert any(e.get("error_class") == "RuntimeError" for e in fallbacks)
