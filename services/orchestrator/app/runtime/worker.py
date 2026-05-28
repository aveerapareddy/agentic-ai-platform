"""Bounded worker: dequeue execution work and invoke orchestrator start path."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from app.runtime.queue import ExecutionWorkItem, InMemoryExecutionQueue
from app.runtime.runtime_meta import read_runtime_meta

if TYPE_CHECKING:
    from app.services.execution_service import ExecutionService


class ExecutionWorker:
    """Consumes queue items; does not invent lifecycle transitions."""

    def __init__(
        self,
        execution_service: ExecutionService,
        queue: InMemoryExecutionQueue,
        *,
        worker_id: str = "worker-1",
    ) -> None:
        self._svc = execution_service
        self._queue = queue
        self._worker_id = worker_id

    @property
    def worker_id(self) -> str:
        return self._worker_id

    def run_once(self) -> bool:
        """Process one queued execution if present. Returns True when work ran."""
        item = self._queue.dequeue()
        if item is None:
            return False
        self._process(item)
        return True

    def _process(self, item: ExecutionWorkItem) -> None:
        now = datetime.now(timezone.utc)
        try:
            from observability import emit_event, get_registry

            get_registry().inc("worker_jobs_total", labels={"worker": self._worker_id})
            emit_event(
                "worker_job_started",
                execution_id=str(item.execution_id),
                worker_id=self._worker_id,
                queue_depth=self._queue.depth(),
            )
        except ImportError:
            pass

        ex = self._svc.get_execution(item.execution_id)
        if ex is None:
            return
        self._svc.record_worker_started(item.execution_id, worker_id=self._worker_id, now=now)

        started = datetime.now(timezone.utc)
        self._svc.start_execution(item.execution_id)
        elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

        try:
            from observability import emit_event, get_registry, observe_latency_ms

            observe_latency_ms(
                "async_execution",
                float(elapsed_ms),
                labels={"worker": self._worker_id},
            )
            get_registry().observe_latency_ms(
                "execution_queue_wait_ms",
                max(
                    0.0,
                    (started - item.enqueued_at).total_seconds() * 1000.0,
                ),
                labels={"worker": self._worker_id},
            )
            meta = read_runtime_meta(self._svc.get_execution(item.execution_id) or ex)
            emit_event(
                "worker_job_completed",
                execution_id=str(item.execution_id),
                worker_id=self._worker_id,
                latency_ms=elapsed_ms,
                cancellation_requested=bool(meta.get("cancellation_requested")),
            )
        except ImportError:
            pass

    def run_until_idle(self, *, max_items: int | None = None) -> int:
        count = 0
        while max_items is None or count < max_items:
            if not self.run_once():
                break
            count += 1
        return count
