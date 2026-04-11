from uuid import uuid4

from common_schemas import (
    Execution,
    ExecutionContext,
    ExecutionMode,
    ExecutionStatus,
)

from evaluation_engine.port import AggregatedMetricFilters
from evaluation_engine.service import EvaluationService
from tests.conftest import FakeStore, utc


def test_get_execution_metrics_none_when_missing() -> None:
    svc = EvaluationService(FakeStore())
    assert svc.get_execution_metrics(uuid4()) is None


def test_get_evaluation_summary_empty_store() -> None:
    svc = EvaluationService(FakeStore())
    summary = svc.get_evaluation_summary(AggregatedMetricFilters(limit=10))
    assert summary.execution_sample_size == 0
    assert summary.evaluation_score is None


def test_get_execution_metrics_with_tenant_from_context() -> None:
    store = FakeStore()
    eid = uuid4()
    cid = uuid4()
    now = utc()
    store.contexts[cid] = ExecutionContext(
        context_id=cid,
        tenant_id="tenant-a",
        request_id="r",
        environment="dev",
        policy_scope="p",
        created_at=now,
        updated_at=now,
    )
    store.executions[eid] = Execution(
        execution_id=eid,
        workflow_type="incident_triage",
        status=ExecutionStatus.COMPLETED,
        execution_mode=ExecutionMode.BACKGROUND,
        execution_context_id=cid,
        trace_timeline=[],
        created_at=now,
        updated_at=now,
        completed_at=now,
    )
    store.steps[eid] = []

    svc = EvaluationService(store)
    m = svc.get_execution_metrics(eid)
    assert m is not None
    assert m.tenant_id == "tenant-a"
