"""Deterministic rule-based classification from frozen execution artifacts."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from common_schemas import (
    ActionProposalStatus,
    ExecutionFeedback,
    ExecutionStatus,
    ImprovementSuggestion,
    MuktiAnalysisInput,
    PatternDetection,
    PolicyDecision,
    StepStatus,
)


class MuktiAnalyzer:
    """Advisory only; outputs ExecutionFeedback without touching live execution rows."""

    def analyze(self, inp: MuktiAnalysisInput, *, now: datetime) -> ExecutionFeedback:
        failure_types: list[str] = []
        patterns: list[PatternDetection] = []
        suggestions: list[ImprovementSuggestion] = []

        ex = inp.execution
        if ex.status == ExecutionStatus.FAILED:
            failure_types.append("terminal_failed")
        if ex.status == ExecutionStatus.CANCELLED:
            failure_types.append("terminal_cancelled")

        for rec in inp.step_records:
            if rec.step.status == StepStatus.FAILED:
                failure_types.append("step_failure")
                break

        for ev in inp.policy_evaluations:
            if ev.decision == PolicyDecision.DENY:
                failure_types.append("policy_evaluation_deny")
                suggestions.append(
                    ImprovementSuggestion(
                        category="policy_rule",
                        summary="Review policy rules that denied this execution path.",
                        detail={"evaluation_id": str(ev.evaluation_id)},
                    ),
                )

        for row in ex.trace_timeline:
            if not isinstance(row, dict):
                continue
            et = row.get("event_type")
            if et == "governed_outcome" and row.get("path") == "policy_denied":
                failure_types.append("trace_policy_denied")
            if et == "model_reasoning" and row.get("path") == "deterministic_fallback":
                patterns.append(
                    PatternDetection(
                        pattern_type="model_deterministic_fallback",
                        description="Structured model path fell back to deterministic StepExecutor.",
                        evidence={
                            "step_id": row.get("step_id"),
                            "task": row.get("task"),
                            "error_class": row.get("error_class"),
                        },
                    ),
                )

        for prop in inp.action_proposals:
            if prop.status == ActionProposalStatus.POLICY_DENIED:
                failure_types.append("action_proposal_policy_denied")
                suggestions.append(
                    ImprovementSuggestion(
                        category="policy_rule",
                        summary="Action proposal reached policy_denied; align workflow intent with policy pack.",
                        detail={"proposal_id": str(prop.proposal_id), "action_type": prop.action_type},
                    ),
                )

        for fb in inp.operator_feedback:
            if any(str(x).lower() == "false_positive" for x in fb.labels):
                patterns.append(
                    PatternDetection(
                        pattern_type="operator_disputed_outcome",
                        description="Operator flagged possible false positive.",
                        evidence={"feedback_record_id": str(fb.feedback_record_id)},
                    ),
                )

        if ex.status == ExecutionStatus.COMPLETED and not failure_types:
            patterns.append(
                PatternDetection(
                    pattern_type="clean_success_path",
                    description="Execution completed with no classified failure signals in this analyzer pass.",
                    evidence={"workflow_type": ex.workflow_type},
                ),
            )

        seen: set[str] = set()
        dedup_failures: list[str] = []
        for x in failure_types:
            if x not in seen:
                seen.add(x)
                dedup_failures.append(x)

        return ExecutionFeedback(
            feedback_id=uuid4(),
            execution_id=ex.execution_id,
            source_scope={"analyzer": "deterministic_rule_pack_v1"},
            failure_types=dedup_failures,
            patterns_detected=patterns,
            improvement_suggestions=suggestions,
            advisory_confidence=0.84,
            created_at=now,
        )
