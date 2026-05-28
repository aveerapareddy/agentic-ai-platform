# Replay investigation — engineering walkthrough

One-line purpose: compare a source execution to a replay child using persisted artifacts and gateway replay APIs.

## Workflow goal

Re-run or sandbox-investigate a prior execution without mutating the source. Operators use **replay** for regression checks and **replay-diff** for structured comparison.

## Execution stages

| Stage | API / owner | Outcome |
|-------|-------------|---------|
| Select source | `GET /v1/executions/{id}` | Confirm terminal or pausable state; inspect trace. |
| Request replay | `POST /v1/executions/{id}/replay` | **202** + `replay_execution_id`; orchestrator `ReplayService`. |
| Child run | orchestrator | New execution with `parent_execution_id`; provenance in `input.__replay_provenance__`. |
| Compare | `GET /v1/executions/{source}/replay-diff/{replay}` | `ReplayDiffSummary` grouped by category/severity. |

## Modes

| Mode | Input | Use |
|------|-------|-----|
| **exact** | Same business input (optional `plan_id`) | Regression / parity check |
| **investigative** | `reason` or `label` + optional `input_overrides` | Sandbox what-if (environment_target) |

## Services involved

- **api-gateway** — RBAC (`operator`+), tenant visibility on source and child.
- **orchestrator** — `ReplayService`, `ReplayDiffService`.
- **evaluation-engine** — diff computation from stored rows (read-only).

## Trace behavior

Child timeline includes `replay_created` (when emitted). Step/tool/policy events follow the same event types as the source workflow.

## Policy behavior

Replay does not bypass policy on **incident_triage** governance: a replayed run that reaches escalation still evaluates **policy-engine** under the child’s execution context.

## Evidence / diff categories

`ReplayDiffCategory`: lineage, execution_status, input, plan, step, model_reasoning, tool_call, policy, validation, result.

Example: [replay-diff-example.json](../examples/replay-diff-example.json).

![Replay comparison](../assets/screenshots/04-replay-comparison.png)

## Console flow

1. Execution detail → **Replay** panel → submit exact or investigative replay.
2. Open child execution or navigate to replay-diff route.
3. Expand diff items by severity (info / warning / significant).

## Related docs

- [replaying-executions.md](../runbooks/replaying-executions.md)
- [replay-architecture diagram](../diagrams/replay-architecture.svg)
- [storage bridge fields](../architecture/storage-design.md#temporary-metadata-bridge-fields)
