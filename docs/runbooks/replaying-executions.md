# Replaying executions

One-line purpose: what **replay** means in this platform, what is implemented in-repo, and how to **inspect** stored executions for review.

## Concept (runtime model and API design)

Replay means re-running or analyzing an execution from **stored** structure and inputs: plan revision, step graph, tool call inputs, policy evaluation inputs, and execution context—or a labeled **investigative** variant with controlled overrides. Structural determinism is the goal; identical LLM outputs are not guaranteed unless inference is pinned (see [runtime-model.md](../architecture/runtime-model.md) §9 and [api-design.md](../architecture/api-design.md) §4.5).

`ReplayRequest` and `ReplayMode` exist in **`packages/common-schemas`** for future gateway/orchestrator endpoints.

## What is not implemented here

There is **no** orchestrator HTTP handler or `ExecutionService.replay(...)` that clones an execution and re-drives the engine from a `source_execution_id`. Treat `POST /v1/executions/{id}/replay` as **specified**, not **wired** in this repository.

## Inspecting stored executions (today)

Use the **repository** port—the same abstraction `ExecutionEngine` uses.

**In-memory (tests / scripts)**

- `InMemoryRepository`: `get_execution`, `list_steps_for_execution`, `get_step_result`, `list_tool_calls_for_step`, `list_policy_evaluations_for_execution`, `list_action_proposals_for_execution`, `get_plan`, `get_context`.

**PostgreSQL**

- Apply `infra/db/migrations/*.sql`, set `ORCHESTRATOR_TEST_DATABASE_URL`, run integration tests or a small script using `PostgresRepository` (see `app/tests/test_postgres_repository_integration.py`).

**Read-only review workflow**

1. Resolve `execution_id` (from logs, test output, or DB query against `executions`).
2. Load execution row → `trace_timeline` JSON, `result`, `validation_summary`.
3. Join steps and step_results for ordered narrative.
4. For `gather_evidence`, list tool calls per step id to see `incident_metadata_tool` / `signal_lookup_tool` audit rows.

## Relation to Mukti

Mukti consumes a **frozen snapshot** via `build_mukti_analysis_input`; that is **analysis of a completed run**, not a full deterministic re-execution. Use it when the goal is pattern detection and advisory feedback, not reproducing side effects.

## Intentional limits

- External systems called by tools in real deployments may return different data on a hypothetical second run; this codebase’s tools are local/fake and repeatable.
- **Exact** replay as an automated job is a future orchestrator feature once the replay API is implemented.
