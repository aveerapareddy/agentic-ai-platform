# Orchestrator application package

Deterministic execution control plane: planning, step scheduling, validation, policy coordination, trace timeline.

## Async execution (Session C)

- **`runtime/queue.py`** — `InMemoryExecutionQueue` (FIFO `execution_id` work items)
- **`runtime/worker.py`** — `ExecutionWorker` calls `ExecutionService.start_execution` (bounded; no invented transitions)
- **`runtime/runtime_meta.py`** — bridge metadata in `executions.input.__orch_runtime_meta__` (`queued_at`, `cancellation_requested`, `worker_id`, …)

`ExecutionMode.BACKGROUND` + gateway `GATEWAY_USE_EXECUTION_WORKER_QUEUE=true` enqueues work; worker thread drains the queue. Synchronous `start_execution` remains for tests and direct invocation.

## Cancellation

`ExecutionService.request_cancellation` sets `cancellation_requested` and transitions to `CANCELLED` when allowed. Orchestrator loop checks between steps; tools honor `cancel_check`.

## Limitations

- In-memory queue (single process)
- Not a distributed workflow engine
- Runtime metadata bridge is temporary until dedicated DB columns
