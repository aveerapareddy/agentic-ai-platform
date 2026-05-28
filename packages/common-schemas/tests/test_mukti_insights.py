"""Mukti v2 insight schema shape."""

from __future__ import annotations

from uuid import uuid4

from common_schemas import (
    CrossExecutionInsight,
    InsightCategory,
    InsightSeverity,
    MuktiInsightsSummary,
    RankedImprovementSuggestion,
)


def test_cross_execution_insight_required_fields() -> None:
    ins = CrossExecutionInsight(
        insight_id=uuid4(),
        category=InsightCategory.TOP_FAILURE_TYPE,
        severity=InsightSeverity.WARNING,
        title="step_failure",
        description="Observed across runs.",
        evidence_count=3,
        affected_workflows=["incident_triage"],
        affected_steps=[],
        suggested_action="Review failing steps.",
        related_execution_ids=[uuid4(), uuid4()],
        rank_score=30,
        evidence={"failure_type": "step_failure", "count": 3},
    )
    assert ins.category == InsightCategory.TOP_FAILURE_TYPE
    assert len(ins.related_execution_ids) == 2


def test_mukti_insights_summary_sections() -> None:
    iid = uuid4()
    ins = CrossExecutionInsight(
        insight_id=iid,
        category=InsightCategory.RECURRING_PATTERN,
        severity=InsightSeverity.INFO,
        title="model_deterministic_fallback",
        description="Pattern repeats.",
        evidence_count=2,
        rank_score=20,
    )
    summary = MuktiInsightsSummary(
        scope_description="test",
        execution_feedback_sample_size=2,
        recurring_patterns=[ins],
        insights=[ins],
        ranked_improvement_suggestions=[
            RankedImprovementSuggestion(
                rank=1,
                category="policy_rule",
                summary="Review deny rules.",
                evidence_count=2,
                suggested_action="Tune policy pack.",
            )
        ],
    )
    assert summary.execution_feedback_sample_size == 2
    assert summary.recurring_patterns[0].insight_id == iid
    assert summary.ranked_improvement_suggestions[0].rank == 1
