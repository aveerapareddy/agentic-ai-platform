# Incident workflow demo

One-line purpose: run **`incident_triage`** locally and know what to inspect in the trace.

## Audience

Engineers validating Phase 2–5 behavior (planner, tools, knowledge, model-runtime, governance) without HTTP gateway.

## How to run

From the repository root:

```bash
cd services/orchestrator
PYTHONPATH=".:../../packages/common-schemas/src:../policy-engine:../tool-runtime:../knowledge-service:../model-runtime:../feedback-service:../mukti-agent" \
  python -m app.main
```

Requires Python 3.11+ and dependencies for those packages (editable installs or path as above).

## Input used by the demo

`app.main` calls `create_execution` with:

- `workflow_type`: `"incident_triage"`
- `input_payload`: `{"incident_id": "demo-1", "severity": "high"}`
- `tenant_id`: `"tenant_demo"`
- `request_id`: `"req-demo"`
- `environment`: `"dev"`
- `policy_scope`: `"default"`

That combination hits the policy **allow** branch for `escalate_incident` (non-prod, not `phase3_deny` / `phase3_conditional`).

## Expected output (stdout)

- Lines showing **created** execution id and status `created`.
- **final** status `completed` for the default demo.
- **result** payload including triage fields (`incident_summary`, `likely_cause`, `evidence_summary`, …) and governance fields (`policy_decision: allow`, `approval_status: not_required`).
- Per-step lines: three steps (`analyze_incident`, `gather_evidence`, `validate_incident`) with `confidence_score` / `completeness` from **step_results**.

## What to look for in the trace

After a run, the in-memory repository inside `main` is not printed; to inspect **trace_timeline** in code, use a small script or pytest pattern:

1. Instantiate `InMemoryRepository`, `ExecutionService(repo)`, same `create_execution` / `start_execution`.
2. Load `repo.get_execution(id).trace_timeline` and assert event types such as `model_reasoning`, `knowledge_retrieved`, `tool_call_completed`, `policy_evaluated`, `governed_outcome`.

Reference tests: `app/tests/test_governance_incident.py` (deny / conditional / approval), Phase 4 integration tests if present for tool rows.

## Variants (policy path)

| Goal | Change |
|------|--------|
| **Deny** | `policy_scope="phase3_deny"` → final `failed`, `policy_decision: deny`. |
| **Awaiting approval** | `policy_scope="phase3_conditional"` or `environment="prod"` → `awaiting_approval`; then `submit_approval(..., decision=approve\|reject)`. |

## Teardown

No background processes; in-memory state exits with the process. For PostgreSQL-backed experiments, use migrations under `infra/db/migrations/` and `ORCHESTRATOR_TEST_DATABASE_URL` per integration tests.
