"""In-memory execution work queue (single-process worker model)."""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class ExecutionWorkItem:
    execution_id: UUID
    enqueued_at: datetime


class InMemoryExecutionQueue:
    """FIFO queue for background execution starts."""

    def __init__(self) -> None:
        self._items: deque[ExecutionWorkItem] = deque()
        self._lock = threading.Lock()

    def enqueue(self, execution_id: UUID, *, now: datetime | None = None) -> int:
        ts = now or datetime.now(timezone.utc)
        with self._lock:
            self._items.append(ExecutionWorkItem(execution_id=execution_id, enqueued_at=ts))
            return len(self._items)

    def dequeue(self) -> ExecutionWorkItem | None:
        with self._lock:
            if not self._items:
                return None
            return self._items.popleft()

    def depth(self) -> int:
        with self._lock:
            return len(self._items)
