from evaluation_engine.anomalies import (
    MIN_EXECUTIONS_FOR_WORKFLOW_RULE,
    MIN_MODEL_EVENTS_SINGLE_EXEC,
    detect_anomalies,
)
from evaluation_engine.models import AggregatedMetrics, ExecutionMetrics, WorkflowTypeRollup


def test_anomaly_high_fallback_single_execution() -> None:
    m = ExecutionMetrics(
        execution_id="x",
        workflow_type="wf",
        execution_status="completed",
        model_reasoning_event_count=MIN_MODEL_EVENTS_SINGLE_EXEC,
        model_reasoning_fallback_event_count=MIN_MODEL_EVENTS_SINGLE_EXEC,
        model_fallback_rate=1.0,
    )
    agg = AggregatedMetrics(executions_in_scope=1)
    findings = detect_anomalies([m], agg)
    assert any(f.code == "high_model_fallback_single_execution" for f in findings)
    assert findings[0].evidence["execution_id"] == "x"


def test_anomaly_workflow_failure_rate() -> None:
    per = [
        ExecutionMetrics(
            execution_id=str(i),
            workflow_type="wf",
            execution_status="failed",
            model_reasoning_event_count=0,
            model_reasoning_fallback_event_count=0,
        )
        for i in range(MIN_EXECUTIONS_FOR_WORKFLOW_RULE)
    ]
    agg = AggregatedMetrics(
        executions_in_scope=len(per),
        by_workflow_type={
            "wf": WorkflowTypeRollup(
                execution_count=MIN_EXECUTIONS_FOR_WORKFLOW_RULE,
                failed_execution_count=MIN_EXECUTIONS_FOR_WORKFLOW_RULE,
            )
        },
    )
    findings = detect_anomalies(per, agg)
    assert any(f.code == "elevated_execution_failure_rate" for f in findings)


def test_no_false_positive_low_fallback() -> None:
    m = ExecutionMetrics(
        execution_id="y",
        workflow_type="wf",
        execution_status="completed",
        model_reasoning_event_count=MIN_MODEL_EVENTS_SINGLE_EXEC,
        model_reasoning_fallback_event_count=0,
        model_fallback_rate=0.0,
    )
    findings = detect_anomalies([m], AggregatedMetrics(executions_in_scope=1))
    assert not any(f.code == "high_model_fallback_single_execution" for f in findings)
