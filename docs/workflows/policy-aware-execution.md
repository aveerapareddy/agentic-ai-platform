# Policy-aware execution

One-line purpose: how **policy-engine** gates the **`escalate_incident`** proposal after **`incident_triage`** validation succeeds in this repository—aligned with `policy_engine.evaluator.PolicyEvaluator` and `ExecutionEngine._finalize_incident_triage_governance`.

## Preconditions

- `workflow_type` must be **`incident_triage`** for the governance block to run after all plan steps succeed in **`validating`**.
- **Execution context** must be loadable (tenant, `environment`, `policy_scope`, etc.)—the policy evaluator reads **ExecutionContext** + **ActionProposal** only; it does not execute tools or call models.

## Scenario description

After structured triage steps complete, the orchestrator always creates an **action_proposal** with `action_type: "escalate_incident"`, `risk_level: high`, and a payload derived from execution input and validation output. It then calls **policy-engine** synchronously. The outcome is one of **allow**, **deny**, or **conditional** (maps to `PolicyDecision` in `common_schemas`).

Other workflows (e.g. generic two-step plan) complete without this proposal path today.

## Where model-runtime, tool-runtime, knowledge-service, policy-engine, and Mukti run

On **this** governance segment only (after triage steps have already finished):

| Capability | Used here? | Notes |
|------------|------------|--------|
| **model-runtime** | No | Model calls occur earlier in `analyze_incident` / `validate_incident`, not during `evaluate_proposal`. |
| **tool-runtime** | No | Escalation is not dispatched through tools in code. |
| **knowledge-service** | No | Retrieval ran in `gather_evidence` if applicable. |
| **policy-engine** | Yes | `PolicyEvaluationService.evaluate_proposal` is the sole external service call on this segment. |
| **Mukti** | No | Post-execution only; see [mukti-agent.md](mukti-agent.md). |

## Step-by-step flow (governance segment)

| Step | Actor | Action |
|------|--------|--------|
| 1 | **orchestrator** | Build `ActionProposal` (`escalate_incident`); `save_action_proposal`; append timeline `action_proposed`. |
| 2 | **policy-engine** | `PolicyEvaluationService.evaluate_proposal(context, proposal)` returns `PolicyEvaluationDraft` (decision, reason, `evaluated_rules`). |
| 3 | **orchestrator** | Assign ids, build `PolicyEvaluation`, `save_policy_evaluation`; timeline `policy_evaluated`. |
| 4 | **orchestrator** | Branch on `draft.decision`: **DENY** → proposal `policy_denied`, execution **FAILED**, `governed_outcome` / `policy_denied`. **ALLOW** → proposal **approved**, execution **COMPLETED**, `governed_outcome` / `policy_allow`. **CONDITIONAL** → proposal **awaiting_approval**, execution **AWAITING_APPROVAL**, timeline `approval_required`. |
| 5 | Human / caller (when conditional) | `ExecutionService.submit_approval` with `ApprovalDecision.approve` or `reject` (defer unsupported in Phase 3). **orchestrator** persists **Approval**, updates proposal and execution to **COMPLETED** or **FAILED**. |

## Services involved

| Concern | Service |
|---------|---------|
| Proposal creation and persistence | **orchestrator** (repository) |
| Rule evaluation | **policy-engine** only |
| Tool execution | **Not** on this segment—escalation is not dispatched to tool-runtime in code |
| Model-runtime / knowledge | **Not** used during policy evaluation |

## Policy evaluation points (implemented rules)

For `escalate_incident`, `PolicyEvaluator` applies (see `RULE_PACK_ID = "phase3_deterministic_v1"`):

1. Unknown `action_type` → **deny**.
2. `policy_scope == "phase3_deny"` → **deny** (`R_SCOPE_DENY`).
3. `environment == "prod"` **or** `policy_scope == "phase3_conditional"` → **conditional** (`R_CONDITIONAL_APPROVAL`).
4. Otherwise (e.g. `dev` + `default`) → **allow** (`R_DEFAULT_ALLOW`).

## Audit trail

- **policy_evaluation** row: `decision`, `reason`, `evaluated_rules`, `subject_ref` (includes `proposal_id`, `action_type`).
- **action_proposal** row: status transitions (`proposed` → `approved` / `policy_denied` / `awaiting_approval` / `rejected`).
- **approval** row when conditional path completes.
- **trace_timeline** events: `action_proposed`, `policy_evaluated`, `governed_outcome`, `approval_required`, `approval_received`, `execution_status`.

## Final result shape (`execution.result`)

Depends on branch:

- **Allow**: `status` → `completed`; `result` includes triage summary fields from `_build_completion_result`, plus `proposed_action`, `policy_decision: "allow"`, `approval_status: "not_required"`.
- **Deny**: `status` → `failed`; `outcome: "failed"`, `policy_decision: "deny"`, `approval_status: "not_applicable"`, `proposed_action` present.
- **Conditional (paused)**: `status` → `awaiting_approval`; `outcome: "awaiting_approval"`, nested `governance` with `proposal_id`, `evaluation_id`, `policy_decision: "conditional"`, `approval_status: "pending"`.
- **After `submit_approval`**: `completed` with `approval_status: "approved"` or `failed` with `approval_status: "rejected"`; `policy_decision` remains `"conditional"` on the success path per current orchestrator payload.

## Tool registration and permissions

Tool calls for incident triage occur only in **`gather_evidence`** and are governed by orchestration order (policy for escalation runs **after** steps). There is **no** separate policy gate on each tool invocation in the current orchestrator loop; risk is concentrated on the escalation proposal. This matches Phase 3 depth, not a full per-tool policy matrix.

## What is out of scope here

- **Automatic rollback** or compensation of external systems: not implemented; deny/fail paths record state only.
- **HTTP** `POST .../approvals` from api-gateway: contract is in [api-design.md](../architecture/api-design.md); wiring is not in the gateway service tree.
- **Replay API** (`POST .../replay`): schema exists in `common_schemas`; orchestrator does not expose a replay runner in this repo (see [replaying-executions.md](../runbooks/replaying-executions.md)).
