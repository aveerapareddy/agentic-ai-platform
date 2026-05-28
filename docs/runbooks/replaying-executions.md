# Replaying executions

One-line purpose: how **replay v2** creates auditable child executions from a source run without mutating the source.

## Modes

| Mode | Behavior |
|------|----------|
| **exact** | Same `workflow_type` and input payload as the source (replay metadata stripped). Runs in `environment_target`. No `input_overrides` or `override_plan`. |
| **investigative** | Same `workflow_type` by default; merges `input_overrides` onto source input. Requires non-empty **reason** or **label**. Records what changed in provenance and trace. |

Both modes create a **new** execution with `parent_execution_id` set to the source. The source execution row and trace are **never updated**.

## API

`POST /v1/executions/{execution_id}/replay` (api-gateway → orchestrator `ReplayService`).

Example (exact):

```json
{
  "mode": "exact",
  "environment_target": "sandbox",
  "label": "post-incident-review",
  "requested_by": "operator@example.com"
}
```

Example (investigative):

```json
{
  "mode": "investigative",
  "environment_target": "sandbox",
  "reason": "test lower severity hypothesis",
  "input_overrides": { "severity": "low" }
}
```

Response (`202`): `ReplayCreatedResponse` with `replay_execution_id`, `status`, `replay_mode`, and full `provenance` object.

Optional `start_execution: true` runs the normal orchestrator loop on the child after creation (policy, validation, and trace rules still apply).

## Provenance storage (bridge)

Until a dedicated replay table exists, provenance is stored at:

- `execution.input["__replay_provenance__"]` (`REPLAY_PROVENANCE_INPUT_KEY` in `common_schemas`)
- Child `trace_timeline` event `replay_created` (source id, mode, reason/label, override summary)

Only `ReplayService` writes this key.

## Listing child replays

`ReplayService.list_replays_for_source(source_execution_id)` uses `Repository.list_executions_by_parent` (no separate gateway route in this session).

## Replay diff (Session 2)

`GET /v1/executions/{source_execution_id}/replay-diff/{replay_execution_id}` returns a **`ReplayDiffSummary`** from orchestrator `ReplayDiffService` (api-gateway delegates via `ReplayDiffFacade`; no diff logic in the route handler).

The engine is **read-only**: it loads stored executions, steps, step results, tool calls, policy evaluations, approvals, and trace timelines. It **does not** re-run either execution or mutate rows.

### Compared dimensions

| Category | What is compared |
|----------|------------------|
| **lineage** | `parent_execution_id`, provenance `source_execution_id`, investigative overrides |
| **execution_status** | `status`, `workflow_type` |
| **input** | Business input (excluding `__replay_provenance__`) |
| **plan** | `current_plan_id`, step count |
| **step** | Order by `created_at`, type, status, agent, step results |
| **model_reasoning** | `trace_timeline` events with `event_type=model_reasoning` (path, task) |
| **tool_call** | Flattened tool calls across steps (name, status, side-effect, idempotency) |
| **policy** | Policy evaluations, approval counts/decisions, action proposal counts |
| **validation** | `validation_summary`, step validation outcomes |
| **result** | Selected top-level `execution.result` keys (not full JSON blobs) |

Severity is rule-based: **significant** (e.g. not linked, status mismatch, step count mismatch, policy deny mismatch), **warning** (input, model path, tool/policy deltas), **info** (minor fields, lineage OK).

### Limitations

- Positional step/tool comparison by `created_at` order — not semantic step-id alignment across replays.
- Does not diff full plan documents or large arbitrary JSON payloads (path-based, bounded fields only).
- Stochastic model output text is not compared — only recorded `model_reasoning` paths/tasks.
- No operator-console visualization in this session.

## Intentional limits (Session 1)

- No replay UI in operator-console.
- `override_plan` is validated but not yet applied to planning (future work).
- Stochastic model outputs may differ on replay; structural inputs and lineage are authoritative per [runtime-model.md](../architecture/runtime-model.md) §9.
- External tool side effects are not stubbed automatically for sandbox replay.

## Inspecting runs manually

See repository port: `get_execution`, `list_steps_for_execution`, `list_executions_by_parent`, trace timeline on child vs source.
