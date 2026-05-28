# Cost attribution workflow

One-line purpose: evidence-backed cost investigation and attribution using the shared execution model (not incident-specific governance).

## Stages

| # | Stage | Owner | Behavior |
|---|--------|--------|----------|
| 1 | Create | **orchestrator** / gateway | `workflow_type=cost_attribution`, structured `input` (`scope_id`, optional `service_id`). |
| 2 | Plan | **Planner** | `analyze_cost_anomaly` → `retrieve_cost_evidence` → `correlate_usage_patterns` → `validate_cost_attribution`. |
| 3 | Analyze | **orchestrator** + **model-runtime** | Bounded `CostAttributionReasoningOutput` or **StepExecutor** fallback. |
| 4 | Retrieve | **orchestrator** + **knowledge-service** | Billing/cost playbook retrieval; timeline `knowledge_retrieved`. |
| 5 | Correlate | **orchestrator** + **tool-runtime** | `cloud_cost_tool`, `metrics_lookup_tool`; timeline `tool_call_completed`. |
| 6 | Validate | **orchestrator** + **model-runtime** | `CostValidationOutput` + `ValidationOutcome`; **VALIDATING** → **COMPLETED** (no escalation governance). |

## Structured outputs

- **Analyze:** `CostAttributionReasoningOutput` — suspected service/team, anomaly type, estimated impact, optimization candidates, evidence references.
- **Retrieve:** `CostEvidenceSummary` fields on step output — evidence summary, chunk ids, corpus version.
- **Validate:** `CostValidationOutput` — confidence, likely service/team, recommended actions.

## Service boundaries

- **model-runtime:** `analyze_cost_anomaly`, `validate_cost_attribution` only.
- **knowledge-service:** `retrieve_cost_evidence` only (metadata filters, corpus version).
- **tool-runtime:** `correlate_usage_patterns` only.

Retrieval supports orchestration evidence; it does not drive step ordering.

## Limitations

- Local in-memory corpus; no distributed ingestion pipeline.
- Semantic scoring is lightweight (token overlap + cosine on term frequencies), not a hosted embedding service.
- No per-step policy gate on tools (same as incident gather path depth).
- Optimization actions are advisory strings only (no autonomous remediation loop).
