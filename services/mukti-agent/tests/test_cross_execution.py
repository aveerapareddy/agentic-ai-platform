"""Cross-execution Mukti v2 ranking and aggregation."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import (
    ExecutionFeedback,
    ExecutionMode,
    ExecutionStatus,
    ExecutionSummary,
    ImprovementSuggestion,
    MuktiCrossExecutionInput,
    PatternDetection,
)

from mukti_agent.cross_execution import CrossExecutionAnalyzer


def _summary(*, wf: str, status: ExecutionStatus = ExecutionStatus.FAILED) -> ExecutionSummary:
    now = datetime.now(timezone.utc)
    return ExecutionSummary(
        execution_id=uuid4(),
        workflow_type=wf,
        status=status,
        execution_mode=ExecutionMode.BACKGROUND,
        created_at=now,
        updated_at=now,
    )


def _feedback(
    execution_id,
    *,
    failure_types: list[str] | None = None,
    patterns: list[PatternDetection] | None = None,
    suggestions: list[ImprovementSuggestion] | None = None,
) -> ExecutionFeedback:
    return ExecutionFeedback(
        feedback_id=uuid4(),
        execution_id=execution_id,
        failure_types=list(failure_types or []),
        patterns_detected=list(patterns or []),
        improvement_suggestions=list(suggestions or []),
        advisory_confidence=0.8,
        created_at=datetime.now(timezone.utc),
    )


def test_ranks_failure_types_by_frequency() -> None:
    s1, s2, s3 = _summary(wf="a"), _summary(wf="b"), _summary(wf="c")
    inp = MuktiCrossExecutionInput(
        execution_feedback=[
            _feedback(s1.execution_id, failure_types=["step_failure"]),
            _feedback(s2.execution_id, failure_types=["step_failure", "terminal_failed"]),
            _feedback(s3.execution_id, failure_types=["terminal_failed"]),
        ],
        execution_summaries=[s1, s2, s3],
    )
    out = CrossExecutionAnalyzer().analyze(inp)
    assert out.top_failure_types
    assert out.top_failure_types[0].title == "step_failure"
    assert out.top_failure_types[0].evidence_count == 2
    assert out.top_failure_types[0].rank_score >= out.top_failure_types[1].rank_score


def test_recurring_pattern_requires_min_two_hits() -> None:
    ex = uuid4()
    pat = PatternDetection(pattern_type="model_deterministic_fallback", description="fb")
    inp = MuktiCrossExecutionInput(
        execution_feedback=[
            _feedback(ex, patterns=[pat]),
            _feedback(uuid4(), patterns=[pat]),
        ],
        execution_summaries=[],
    )
    out = CrossExecutionAnalyzer().analyze(inp)
    assert any(i.title == "model_deterministic_fallback" for i in out.recurring_patterns)


def test_ranked_suggestions_ordered_by_evidence() -> None:
    e1, e2 = uuid4(), uuid4()
    sug = ImprovementSuggestion(category="policy_rule", summary="Review deny rules.")
    inp = MuktiCrossExecutionInput(
        execution_feedback=[
            _feedback(e1, suggestions=[sug]),
            _feedback(e2, suggestions=[sug]),
        ],
        execution_summaries=[],
    )
    out = CrossExecutionAnalyzer().analyze(inp)
    assert out.ranked_improvement_suggestions
    assert out.ranked_improvement_suggestions[0].rank == 1
    assert out.ranked_improvement_suggestions[0].evidence_count == 2
