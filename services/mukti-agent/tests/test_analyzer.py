"""Deterministic Mukti classification and advisory output shape."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import (
    Execution,
    ExecutionMode,
    ExecutionStatus,
    FeedbackSource,
    MuktiAnalysisInput,
    OperatorFeedback,
)

from mukti_agent.service import MuktiService


def _minimal_execution(*, status: ExecutionStatus, timeline: list | None = None) -> Execution:
    now = datetime.now(timezone.utc)
    return Execution(
        execution_id=uuid4(),
        workflow_type="incident_triage",
        status=status,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=uuid4(),
        input={},
        trace_timeline=list(timeline or []),
        created_at=now,
        updated_at=now,
    )


def test_clean_success_adds_pattern() -> None:
    ex = _minimal_execution(status=ExecutionStatus.COMPLETED)
    inp = MuktiAnalysisInput(execution=ex, step_records=[])
    out = MuktiService().analyze(inp)
    assert out.execution_id == ex.execution_id
    assert out.advisory_confidence == 0.84
    types = {p.pattern_type for p in out.patterns_detected}
    assert "clean_success_path" in types
    assert out.failure_types == []


def test_trace_policy_denied_failure_type() -> None:
    ex = _minimal_execution(
        status=ExecutionStatus.FAILED,
        timeline=[
            {
                "event_type": "governed_outcome",
                "path": "policy_denied",
                "proposal_id": str(uuid4()),
            },
        ],
    )
    inp = MuktiAnalysisInput(execution=ex, step_records=[])
    out = MuktiService().analyze(inp)
    assert "trace_policy_denied" in out.failure_types
    assert "terminal_failed" in out.failure_types


def test_model_fallback_pattern() -> None:
    ex = _minimal_execution(
        status=ExecutionStatus.COMPLETED,
        timeline=[
            {"event_type": "model_reasoning", "path": "deterministic_fallback", "task": "analyze_incident"},
        ],
    )
    inp = MuktiAnalysisInput(execution=ex, step_records=[])
    out = MuktiService().analyze(inp)
    assert any(p.pattern_type == "model_deterministic_fallback" for p in out.patterns_detected)


def test_operator_false_positive_pattern() -> None:
    ex = _minimal_execution(status=ExecutionStatus.COMPLETED)
    fb = OperatorFeedback(
        feedback_record_id=uuid4(),
        execution_id=ex.execution_id,
        source=FeedbackSource.OPERATOR_CONSOLE,
        labels=["false_positive"],
        detail={},
        created_at=datetime.now(timezone.utc),
    )
    inp = MuktiAnalysisInput(execution=ex, step_records=[], operator_feedback=[fb])
    out = MuktiService().analyze(inp)
    assert any(p.pattern_type == "operator_disputed_outcome" for p in out.patterns_detected)


def test_suggestions_structured_not_empty_on_policy_deny_eval() -> None:
    from common_schemas import PolicyDecision, PolicyEvaluation

    ex = _minimal_execution(status=ExecutionStatus.FAILED)
    ev = PolicyEvaluation(
        evaluation_id=uuid4(),
        execution_id=ex.execution_id,
        execution_context_id=uuid4(),
        decision=PolicyDecision.DENY,
        reason="test",
        evaluated_rules=[],
        subject_ref={"type": "proposal"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    inp = MuktiAnalysisInput(execution=ex, step_records=[], policy_evaluations=[ev])
    out = MuktiService().analyze(inp)
    assert "policy_evaluation_deny" in out.failure_types
    assert out.improvement_suggestions
    assert out.improvement_suggestions[0].category == "policy_rule"
