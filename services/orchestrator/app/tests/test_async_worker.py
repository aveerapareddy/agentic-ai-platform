"""Async queue, worker, and cancellation foundations."""

from __future__ import annotations

from common_schemas import ExecutionMode, ExecutionStatus

from app.adapters.repository import InMemoryRepository
from app.runtime.queue import InMemoryExecutionQueue
from app.runtime.runtime_meta import is_cancellation_requested, read_runtime_meta
from app.runtime.worker import ExecutionWorker
from app.services.execution_service import ExecutionService


def test_queue_enqueue_dequeue() -> None:
    q = InMemoryExecutionQueue()
    from uuid import uuid4

    eid = uuid4()
    assert q.enqueue(eid) == 1
    item = q.dequeue()
    assert item is not None
    assert item.execution_id == eid
    assert q.dequeue() is None


def test_worker_runs_background_execution_to_completion() -> None:
    repo = InMemoryRepository()
    q = InMemoryExecutionQueue()
    svc = ExecutionService(repo, queue=q)
    worker = ExecutionWorker(svc, q)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "async-1"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
        execution_mode=ExecutionMode.BACKGROUND,
    )
    svc.enqueue_execution(ex.execution_id)
    assert worker.run_once() is True
    done = repo.get_execution(ex.execution_id)
    assert done is not None
    assert done.status == ExecutionStatus.COMPLETED
    meta = read_runtime_meta(done)
    assert meta.get("worker_id")


def test_cancellation_request_stops_before_completion() -> None:
    repo = InMemoryRepository()
    svc = ExecutionService(repo)
    ex = svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "cancel-1"},
        tenant_id="t",
        request_id="r",
        environment="dev",
        policy_scope="default",
    )
    svc.request_cancellation(ex.execution_id, reason="test")
    cancelled = repo.get_execution(ex.execution_id)
    assert cancelled is not None
    assert cancelled.status == ExecutionStatus.CANCELLED
    assert is_cancellation_requested(cancelled) is True
