"""Rule-based anomaly flags over metrics (thresholds are explicit constants, not learned)."""

from __future__ import annotations

from evaluation_engine.models import AggregatedMetrics, AnomalyFinding, ExecutionMetrics

# Documented thresholds — tune via configuration in a later phase; values are transparent.
HIGH_FALLBACK_RATE = 0.45
MIN_MODEL_EVENTS_SINGLE_EXEC = 4
ELEVATED_WORKFLOW_FAILURE_RATE = 0.35
MIN_EXECUTIONS_FOR_WORKFLOW_RULE = 5
POLICY_DENY_SHARE = 0.25
MIN_POLICY_EVALS_FOR_DENY_RULE = 6


def detect_anomalies(
    per_execution: list[ExecutionMetrics],
    aggregated: AggregatedMetrics,
) -> list[AnomalyFinding]:
    findings: list[AnomalyFinding] = []

    for m in per_execution:
        if m.model_reasoning_event_count >= MIN_MODEL_EVENTS_SINGLE_EXEC:
            rate = m.model_fallback_rate
            if rate is not None and rate >= HIGH_FALLBACK_RATE:
                findings.append(
                    AnomalyFinding(
                        code="high_model_fallback_single_execution",
                        severity="elevated",
                        explanation=(
                            "Model reasoning fallback share exceeds threshold for this execution "
                            f"({rate:.2f} >= {HIGH_FALLBACK_RATE})."
                        ),
                        evidence={
                            "execution_id": m.execution_id,
                            "model_reasoning_event_count": m.model_reasoning_event_count,
                            "model_reasoning_fallback_event_count": m.model_reasoning_fallback_event_count,
                            "threshold": HIGH_FALLBACK_RATE,
                        },
                    )
                )

    for wf, roll in aggregated.by_workflow_type.items():
        if roll.execution_count >= MIN_EXECUTIONS_FOR_WORKFLOW_RULE:
            fr = roll.failed_execution_count / roll.execution_count
            if fr >= ELEVATED_WORKFLOW_FAILURE_RATE:
                findings.append(
                    AnomalyFinding(
                        code="elevated_execution_failure_rate",
                        severity="warning",
                        explanation=(
                            f"Workflow {wf!r} failure rate {fr:.2f} "
                            f">= {ELEVATED_WORKFLOW_FAILURE_RATE} over "
                            f"{roll.execution_count} executions."
                        ),
                        evidence={
                            "workflow_type": wf,
                            "failed_execution_count": roll.failed_execution_count,
                            "execution_count": roll.execution_count,
                        },
                    )
                )

    total_evals = sum(r.evaluation_count for r in aggregated.by_policy_decision.values())
    deny = aggregated.by_policy_decision.get("deny")
    if deny and total_evals >= MIN_POLICY_EVALS_FOR_DENY_RULE:
        share = deny.evaluation_count / total_evals
        if share >= POLICY_DENY_SHARE:
            findings.append(
                AnomalyFinding(
                    code="high_policy_deny_share",
                    severity="elevated",
                    explanation=(
                        f"Policy deny evaluations are {share:.2f} of all evaluations "
                        f"(threshold {POLICY_DENY_SHARE})."
                    ),
                    evidence={
                        "deny_evaluation_count": deny.evaluation_count,
                        "total_policy_evaluations": total_evals,
                    },
                )
            )

    return findings
