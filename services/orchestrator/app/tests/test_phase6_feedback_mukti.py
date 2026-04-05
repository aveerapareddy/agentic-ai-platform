"""Phase 6: post-execution feedback ingestion and Mukti analysis (no live mutation)."""

from __future__ import annotations

from common_schemas import ExecutionStatus, FeedbackSource

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService
from app.support.mukti_input import build_mukti_analysis_input
from feedback_service.service import FeedbackService
from mukti_agent.service import MuktiService


def test_post_execution_mukti_does_not_mutate_execution() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    fb_svc = FeedbackService()
    ex = exec_svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "p6-1"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    done = exec_svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED
    before = repo.get_execution(ex.execution_id)
    assert before is not None

    fb_svc.submit_operator_feedback(
        execution_id=ex.execution_id,
        source=FeedbackSource.OPERATOR_CONSOLE,
        labels=["post_mortem_ok"],
        detail={},
    )
    op_list = fb_svc.list_operator_feedback_for_execution(ex.execution_id)
    inp = build_mukti_analysis_input(repo, ex.execution_id, operator_feedback=op_list)
    mukti_out = MuktiService().analyze(inp)
    fb_svc.save_execution_feedback(mukti_out)

    after = repo.get_execution(ex.execution_id)
    assert after is not None
    assert after.status == before.status
    assert after.trace_timeline == before.trace_timeline

    stored = fb_svc.list_execution_feedback_for_execution(ex.execution_id)
    assert len(stored) == 1
    assert stored[0].feedback_id == mukti_out.feedback_id
    assert any(p.pattern_type == "clean_success_path" for p in stored[0].patterns_detected)


def test_operator_feedback_visible_to_mukti_input() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    fb_svc = FeedbackService()
    ex = exec_svc.create_execution(
        workflow_type="generic",
        input_payload={},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="p",
    )
    exec_svc.start_execution(ex.execution_id)
    fb_svc.submit_operator_feedback(
        execution_id=ex.execution_id,
        source=FeedbackSource.API,
        labels=["false_positive"],
        detail={"reason": "test"},
    )
    op_list = fb_svc.list_operator_feedback_for_execution(ex.execution_id)
    inp = build_mukti_analysis_input(repo, ex.execution_id, operator_feedback=op_list)
    assert len(inp.operator_feedback) == 1
    out = MuktiService().analyze(inp)
    assert any(p.pattern_type == "operator_disputed_outcome" for p in out.patterns_detected)
