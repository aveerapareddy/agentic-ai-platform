"""Phase 4: gather_evidence uses tool-runtime and knowledge-service; trace + evidence."""

from __future__ import annotations

from common_schemas import ExecutionStatus

from app.adapters.repository import InMemoryRepository
from app.runtime.orchestrator import ExecutionEngine
from app.services.execution_service import ExecutionService


def _gather_step(repo: InMemoryRepository, execution_id):
    steps = repo.list_steps_for_execution(execution_id)
    for s in steps:
        if s.input.get("planner_step_name") == "gather_evidence":
            return s
    return None


def test_gather_evidence_persists_tool_calls_and_evidence() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "phase4-1"},
        tenant_id="tenant_a",
        request_id="req-phase4",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    g = _gather_step(repo, ex.execution_id)
    assert g is not None
    tcs = repo.list_tool_calls_for_step(g.step_id)
    assert len(tcs) == 2
    names = {tc.tool_name for tc in tcs}
    assert names == {"incident_metadata_tool", "signal_lookup_tool"}
    for tc in tcs:
        assert tc.status.value == "success"
    res = repo.get_step_result(g.step_id)
    assert res is not None
    assert res.evidence
    types = {e.get("type") for e in res.evidence}
    assert "knowledge_retrieval" in types
    assert "knowledge_chunk" in types
    assert "tool_invocation" in types
    assert res.output and res.output.get("retrieval_id")
    assert res.output.get("tool_call_ids")


def test_trace_includes_knowledge_and_tool_events() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"id": "trace-1"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    assert any(e.get("event_type") == "knowledge_retrieved" for e in done.trace_timeline)
    tool_events = [e for e in done.trace_timeline if e.get("event_type") == "tool_call_completed"]
    assert len(tool_events) >= 2


def test_execution_without_capabilities_falls_back_to_step_executor() -> None:
    repo = InMemoryRepository()
    engine = ExecutionEngine(repo, tool_runtime=None, knowledge_service=None)
    svc = ExecutionService(repo, engine=engine)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "fallback"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    g = _gather_step(repo, ex.execution_id)
    assert g is not None
    assert repo.list_tool_calls_for_step(g.step_id) == []
