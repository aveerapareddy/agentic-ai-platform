# Storage design

One-line purpose: categorize persisted data and what exists today versus what remains conceptual.

## Operational data (implemented)

**PostgreSQL** (see `infra/db/migrations/001_initial_schema.sql` and `002_operator_feedback.sql`):

- **execution_context**, **executions** (includes `trace_timeline` JSONB for ordered events; normalized detail in sibling tables).
- **execution_plans**, **execution_steps**, **step_results** (output + `evidence` JSONB).
- **tool_calls** (FK to execution, step, context).
- **action_proposals**, **policy_evaluations**, **approvals**.
- **execution_feedback** (Mukti advisory rows); **operator_feedback** (human/integration labels)—per `002_operator_feedback.sql`.
- **execution_feedback.advisory_confidence** optional numeric column (migration 002).

**In-memory equivalents** in `InMemoryRepository` and `InMemoryFeedbackRepository` for unit tests and `app.main` demo.

## Artifacts

**Runtime model** allows large binaries or exports outside the OLTP store (constitution §5.2). **This repository** does not implement object storage or artifact URIs in step results beyond JSON-sized payloads in PostgreSQL. Future: S3/GCS-style pointers in `step_results.output` or side tables—**not present** now.

## Retrieval data

**knowledge-service** holds an **in-process corpus** (keyword-ranked documents) in the current implementation. It is **not** backed by a separate vector index or warehouse in this tree; that separation is **architectural intent** (indexes owned by knowledge-service, not the execution DB).

## Caching

No dedicated cache layer is implemented. Read paths hit repository or in-memory structures directly.

## Analytics

No OLAP or warehouse integration. **Mukti** writes **execution_feedback** suitable for downstream batch consumption; no ETL is defined in-repo.

## Retention

Not enforced in application code. Operators are expected to apply database retention and legal hold policies at deployment time.

## Temporary metadata bridge fields

Reserved keys inside `executions.input` (JSONB) until dedicated columns or tables exist. They are **not** part of the public HTTP create contract—clients must not send them on `POST /v1/executions`. Orchestrator and gateway may strip or reject overrides of reserved keys on replay.

| Field | Owner | Purpose | Future migration | Public API contract |
|-------|--------|---------|------------------|---------------------|
| `__replay_provenance__` | **orchestrator** (`ReplayService`) | Lineage for replay children: source execution id, mode, label, reason, overrides metadata. Consumed by replay-diff and operator-console display. | Dedicated `replay_runs` (or similar) table with FK to parent/child executions; strip from `input` on read/write. | **No** — internal persistence bridge. Constant: `REPLAY_PROVENANCE_INPUT_KEY` in `common_schemas.execution`. |
| `__orch_execution_mode__` | **orchestrator** (`PostgresRepository` / in-memory adapter) | Round-trip `execution_mode` (`interactive` / `background`) because `001_initial_schema.sql` has no `execution_mode` column. | Add `executions.execution_mode` column; stop writing this key. | **No** — set from gateway `execution_mode` on create only; not echoed as a stable client field. |
| `__orch_runtime_meta__` | **orchestrator** (`app.runtime.runtime_meta`) | Worker queue and cancellation bridge: `queued_at`, `worker_id`, `cancellation_requested`, timestamps. | Columns or a small `execution_runtime` side table. | **No** — operator cancel flows set this via orchestrator/gateway, not via arbitrary client input. |

**Why they exist:** ship durable behavior without blocking on schema migrations. **Risk:** keys must stay namespaced (`__…__`) and documented so workflow payloads never collide.

**Gateway / UI:** may read provenance for display; must not treat bridge blobs as authoritative policy or trace data.
