# Runtime model

Design artifact: internal definition of how work is represented, progressed, observed, and reproduced in the Agentic AI Platform. This document governs orchestration behavior, storage expectations for traces, and contract boundaries between services. It is not an API specification and does not prescribe storage engines or implementation languages.

## 1. Overview

The runtime is responsible for coordinating **explicit, step-based execution** of multi-agent workflows: accepting scoped inputs, producing an inspectable **Execution Plan**, driving steps through bounded agents and registered tools, enforcing policy at defined decision points, recording a complete **Trace**, and gating completion on validation where required.

An **explicit execution model** is required because enterprise use cases (incident triage, cost attribution, policy-aware actions) demand auditability, replay for post-incident review, deterministic controls for high-risk operations, and clear separation between reasoning, policy, and side effects. Implicit or purely conversational flows do not provide stable identifiers, stable step boundaries, or sufficient material for compliance and operations.

## 2. Core Concepts

| Concept | Definition |
|--------|------------|
| **Execution** | A single end-to-end run of a workflow from accepted input through terminal state (`completed`, `failed`, or `cancelled`), identified by a stable `execution_id`. |
| **Execution context** | The first-class carrier of tenant, principal, environment, correlation ids, and policy-relevant scope. It accompanies every execution, step, **Tool Call**, and policy evaluation so multi-tenant correctness, auditability, and environment isolation hold end to end. |
| **Execution Plan** | A structured, versioned description of intended work: goal, ordered or partially ordered steps, and dependencies. Plans are machine-readable and operator-inspectable; revisions append history rather than erasing it. |
| **Step** | The atomic unit of work the orchestrator schedules. Each step has a type, owning agent (or executor role), inputs, **Step Result**, and lifecycle status. |
| **Agent** | A bounded logical role that produces plans or step outputs under explicit contracts (input/output schemas, allowed tool surfaces). Agents do not bypass policy or tool registration. |
| **Tool** | A registered capability invoked only through the tool runtime: named operation, declared contracts (side-effect class, idempotency, bounds), schema-validated inputs/outputs, permissioned and audited on every **Tool Call**. |
| **Policy** | Rules evaluated by the policy engine (separate from agent logic) that return allow/deny/conditional decisions with reasons and rule references. Evaluations consume **Execution context** and tool side-effect class. |
| **Trace** | The append-only or append-oriented record linking execution, steps, **Tool Calls**, policy evaluations, approvals, validation outcomes, and timestamps into one coherent timeline. |

## 3. Core entities

Fields below are **semantic**: names and meanings are stable contracts for the platform; physical encoding (column layout, serialization format) is out of scope.

### 3.1 Execution

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `execution_id` | Globally unique identifier for this run. |
| `workflow_type` | Declares which platform workflow template applies (e.g. incident triage, cost attribution); drives defaults for validators and policy packs. |
| `status` | Coarse lifecycle state; see Section 4. |
| `execution_context` | Reference to **Execution context** (Section 3.2) bound for the run. |
| `input` | Initial payload and metadata supplied by the caller (subject to schema for the workflow type). |
| `plan` | Reference to or embedded **Execution Plan** for this run (may be absent until planning completes). |
| `steps` | Ordered or addressable collection of **Steps**; authoritative list for scheduling and trace correlation. |
| `result` | Terminal **Step Result** or aggregated outcome for the execution, populated only when completion criteria are met. |
| `timestamps` | `created_at`, `updated_at`, and optionally `completed_at` / `cancelled_at` for SLA and audit. |
| `parent_execution_id` | Optional link for child or continuation runs. |

**Meaning:** An execution is the durable unit of work operators and auditors reference. It subsumes planning, all step attempts, policy decisions, **Tool Calls**, validation, and terminal outcome. It is not a chat session; it is a governed run with a finite exit.

---

### 3.2 Execution context

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `context_id` | Identifier for this context record (may be 1:1 with `execution_id` or stable per request). |
| `tenant_id` | Tenant or organizational partition for data and policy. |
| `principal_id` / `actor` | Authenticated principal or service identity initiating or continuing the run. |
| `request_id` | Correlates logs and upstream gateway requests across services. |
| `environment` | Deployment slice (e.g. dev, staging, prod) for isolation and configuration selection. |
| `permissions_scope` | Effective entitlements or role bindings used for tool allow-lists and data access. |
| `policy_scope` | Policy pack, rule-set version, or evaluation namespace applied to this run. |
| `feature_flags` | Optional toggles affecting behavior; must appear in **Trace** when they influence branching. |

**Meaning:** **Execution context** is passed through the orchestrator, **Tool Call** execution, policy evaluation, and **Trace** emission. It is required for multi-tenant correctness (no cross-tenant tool or data access), auditability (who acted, in which tenant and environment), and environment isolation (prod executions must not read dev configuration implicitly). Policy and tool runtime both consume the same context facts supplied by the platform—not inferred ad hoc by agents.

---

### 3.3 Execution Plan

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `plan_id` | Unique identifier for this plan revision within the execution. |
| `plan_version` | Monotonic or otherwise comparable version within the execution’s plan lineage. |
| `parent_plan_id` | Prior plan revision superseded by this one; null for the first plan. |
| `revision_reason` | Classified rationale for re-plan (e.g. planner retry, validation-driven decomposition, operator directive). |
| `goal` | Declared objective in structured form (not free-form only); aligns validators and policy scope. |
| `steps` | Abstract step specifications: types, agent bindings, inputs templates or references, dependency graph membership. |
| `dependencies` | Directed edges or references defining partial order (which steps must finish before others start). |
| `ordering` | Explicit topological schedule hints or declared **sequential** vs **parallel** groups where independent, policy-approved concurrency is allowed (Section 6). |
| `metadata` | Planner version, model or agent identifiers (if applicable), confidence summaries, and planning-time warnings—without embedding policy decisions. |

**Meaning:** **Execution Plans** are **structured and inspectable** artifacts. Re-planning **creates a new auditable revision** (`plan_id`, incremented `plan_version`, `parent_plan_id`, `revision_reason`); prior revisions remain referenced in the **Trace**. Plan evolution must stay inspectable for replay, debugging, and post-execution analysis (including Mukti) without rewriting history.

---

### 3.4 Step

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `step_id` | Unique within the execution. |
| `type` | Enumerated step kind (e.g. plan, retrieve, reason, tool_batch, validate, human_review)—workflow-specific extensions allowed with registration. |
| `agent` | Bounded agent role or implementation id responsible for producing the step’s primary **Step Result**. |
| `input` | Resolved inputs for this attempt (after parameter binding from execution input and prior steps). |
| `status` | Step-level lifecycle (pending, running, succeeded, failed, skipped, cancelled). |
| `dependencies` | Incoming dependency refs; scheduler must not start until satisfied. |
| `retry_count` | Number of retried attempts for this step identity (see Section 8). |
| `degraded_allowed` | When true, **Execution Plan** declares this step may fail or skip without failing the execution (Section 7); otherwise false. |

**Meaning:** Steps are the **unit of execution** the orchestrator schedules. Agents act *within* steps; tools are invoked *from* steps via the tool runtime as **Tool Calls**, not ad hoc.

---

### 3.5 Step Result

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `step_id` | Links back to the step. |
| `output` | Primary structured output (may be partial when failure handling policy permits recording partial state). |
| `evidence` | Citations, retrieval pointers, excerpts, or references supporting the output—mandatory where workflow rules require traceable grounding. |
| `tool_calls` | List of **Tool Call** records executed during this step (may be empty). |
| `errors` | Normalized error objects (code, message, safe detail for operators). |
| `latency` | Duration or timestamps for performance and SLO accounting. |
| `confidence` | Optional calibrated or ordinal confidence for downstream validation and display—advisory only; see Section 10 (**Confidence vs validation**). |
| `completeness` | Declared completeness (e.g. full, partial, degraded) when **Execution Plan** allows degraded paths; must align with evidence gaps recorded in **Trace**. |

---

### 3.6 Tool contract (registration)

Registration metadata for every tool—stored with tool definitions, enforced at **Tool Call** time:

| Field | Purpose |
|-------|---------|
| `tool_name` | Stable registry name. |
| `side_effect_class` | **read_only** or **state_changing** (policy and retry semantics depend on this). |
| `idempotency` | **idempotent** or **non_idempotent** under declared keying or semantics; drives automatic retry rules (Section 8). |
| `timeout_bounds` | Maximum duration or deadline class the runtime enforces for **Tool Calls** to this tool. |
| `input_schema` / `output_schema` | Contract for schema-validated **Tool Call** arguments and results at the boundary. |

**Meaning — retry and policy:** Orchestrator retries depend on **idempotency**, transient error classification, and **side_effect_class**. Policy evaluation must treat **state_changing** and **non_idempotent** **Tool Calls** under stricter allow and approval rules than read-only idempotent reads.

**Side-effect boundary:** **State_changing** **Tool Calls** run only after successful **Policy evaluation** for the governed proposal or call path. If policy requires **Approval**, the execution remains in `awaiting_approval` until **Approval** is resolved; no **state_changing** **Tool Call** runs in that window. **Non_idempotent** **Tool Calls** are not retried automatically unless policy or workflow explicitly allows that retry mode.

---

### 3.7 Tool Call

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `tool_call_id` | Unique within the trace. |
| `tool_name` | Registered name as defined in **Tool contract** (Section 3.6). |
| `input` | Arguments after schema validation at the tool boundary. |
| `output` | Result or redacted summary if sensitive. |
| `status` | success, failure, timeout, rejected_by_policy. |
| `latency` | Measured server-side execution window. |
| `error` | Structured failure when `status` is not success. |
| `execution_context_ref` | Link to the **Execution context** in effect for this call (must match parent execution). |

Every **Tool Call** is emitted to the **Trace** and tied to a step and execution for audit.

---

### 3.8 Action proposal

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `proposal_id` | Unique identifier. |
| `action_type` | Class of side effect (e.g. ticket_update, infra_change, data_export). |
| `payload` | Structured parameters required to perform the action if approved. |
| `risk_level` | Platform-defined ordinal (e.g. low, medium, high) affecting policy rules and approval defaults. |
| `requires_approval` | Boolean or enum derived from policy; may force `awaiting_approval` on the execution. |

Proposals are how agents express **intent to mutate external state** without performing it until policy and optional human approval complete.

---

### 3.9 Policy evaluation

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `evaluation_id` | Unique identifier. |
| `decision` | `allow`, `deny`, or `conditional` (conditional may mandate approval, narrowed scope, or extra validation). |
| `reason` | Human-readable summary safe for operators. |
| `evaluated_rules` | List of rule ids and versions that fired; supports audit and debugging. |
| `subject_ref` | What was evaluated (e.g. action proposal id, **Tool Call** id, execution transition). |
| `execution_context_ref` | **Execution context** snapshot or id under which evaluation occurred. |

Policy evaluation is performed by the **policy engine** on explicit requests; agents supply facts, not decisions.

---

### 3.10 Approval

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `approval_id` | Unique identifier. |
| `approver` | Principal or role fulfillment reference. |
| `decision` | approve, reject, defer. |
| `timestamp` | When recorded. |
| `notes` | Optional justification (may be mandatory for high risk). |

Approvals apply to proposals or conditional policy outcomes; they are part of the **Trace** and may gate **Tool Call** invocation or execution completion.

---

### 3.11 Trace

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `trace_id` | Identifier for the trace artifact (may equal `execution_id` or be linked). |
| `execution_id` | Anchor execution. |
| `execution_context` | Reference or summary for correlation and audit. |
| `steps` | Sequence or graph of step records with **Step Results**. |
| `tool_calls` | Flat or nested index of all **Tool Calls**. |
| `policy_decisions` | Ordered policy evaluations. |
| `timeline` | Ordered events with monotonic timestamps and event types (step_started, tool_finished, policy_denied, validation_failed, etc.). |

The **Trace** is the **authoritative observability substrate** for replay, debugging, evaluation exports, and Mukti Agent input.

**Trace completeness:** The **Trace** must retain enough to reconstruct why the run ended as it did when external systems are unavailable: resolved **inputs** and material **outputs** (or redaction notes), every **Tool Call** with outcome, every **Policy evaluation** affecting allow/deny, and **validation** outcomes tied to promoted or blocked results.

---

### 3.12 Execution Feedback (Mukti)

**Pseudo-schema**

| Field | Purpose |
|-------|---------|
| `feedback_id` | Unique identifier. |
| `execution_id` | Execution analyzed (or batch reference if aggregated). |
| `failure_types` | Classified issues (e.g. tool_timeout, planner_loop, validation_miss, policy_ambiguity). |
| `patterns_detected` | Cross-run or within-run patterns (e.g. repeated tool selection failure). |
| `improvement_suggestions` | Structured recommendations: prompt or tooling gaps, policy rule additions, validator coverage—**non mutating** on live runs. |

Mukti outputs are **advisory signals** stored and routed to owners; they do not change an in-flight execution (Section 11).

## 4. Execution lifecycle

Terminal and non-terminal states:

| Status | Meaning |
|--------|---------|
| `created` | Execution accepted, identifiers allocated, **Execution context** bound, minimal validation passed. |
| `planning` | Planning agents produce or revise the **Execution Plan**. |
| `executing` | Steps are being scheduled and run; **Tool Calls** and agent work occur here. |
| `validating` | Validators run on non-trivial outputs before exposure or finalization. |
| `awaiting_approval` | Conditional policy or risk requires explicit approval before continuing or completing. |
| `completed` | Success path: validation satisfied, mandatory policy/approvals cleared, result sealed. |
| `failed` | Unrecoverable error per policy, validation failure where blocking, denied action, or unhandled exception class—recorded with terminal cause in **Trace**. |
| `cancelled` | Operator or caller cancellation; in-flight steps torn down per policy; partial **Trace** retained. |

**Transitions (informal)**

- `created` → `planning` when orchestration begins.
- `planning` → `executing` when an **Execution Plan** revision is accepted (or → `failed` if planning exhausts retries).
- During `executing`, a step may trigger policy on a proposal → `awaiting_approval` → back to `executing` on approval, or `failed` on deny.
- Before presenting certain results, orchestrator moves to `validating` → `executing` (if fixes require another step) or `completed` / `failed`.
- `failed` and `cancelled` are terminal. No silent downgrade from `failed` to `completed`.

Invalid transitions are rejected by the orchestrator and logged.

## 5. Execution invariants

The following rules hold across implementations; violations are defects.

1. Every **Step** reaches a terminal step status (`succeeded`, `failed`, `skipped`, or `cancelled`) before the **Execution** reaches a terminal run state (`completed`, `failed`, or `cancelled`).
2. Every **Tool Call** is recorded in the **Trace** before its outcome influences downstream steps or completion.
3. No **Action proposal** may produce external side effects without a preceding **Policy evaluation** on that path; conditional paths require resolved **Approval** when policy mandates it.
4. No **Execution** reaches `completed` without applicable **Validation** unless the **workflow_type** explicitly exempts that path (exemption recorded in **Trace**).
5. **Execution Plan** revisions append auditable lineage (`parent_plan_id`, `plan_version`); history is never silently discarded.
6. The **Trace** reflects each decision point that materially affects outcome (policy, approval, validation, terminal failure or success).

## 6. Step execution model

**Selection:** The orchestrator chooses **ready** steps whose dependencies are satisfied and whose preconditions (workflow-specific) hold. Tie-breaking is deterministic (e.g. stable sort on `step_id`) unless the **Execution Plan** explicitly defines independent parallel groups.

**Dependencies:** A dependency edge means the dependent step must not start until the upstream step reaches a terminal success state (or a documented “soft dependency” variant, if allowed by workflow type—default is strict).

**Sequential vs parallel:** **Parallel execution is allowed only for steps the Execution Plan marks as independent and safe for concurrent execution**, and only when the active **policy_scope** permits that concurrency (no conflicting **state_changing** **Tool Calls**, no shared mutable resource without a defined locking strategy). **Conservative sequential scheduling within the ready set is the default** when either workflow or policy does not explicitly allow parallelism. Both workflow constraints and policy constraints must permit parallelism; if either withholds consent, steps run sequentially.

**Agent invocation:** For each running step, the orchestrator passes resolved `input`, full **Execution context**, and pointers to allowed tools. The agent returns outputs that conform to the step contract; **Tool Calls** flow through the tool runtime only. Agents cannot self-elevate permissions or skip validation hooks.

## 7. Failure semantics

**Failure types**

| Type | Typical source | Trace signal |
|------|----------------|--------------|
| Tool | Tool runtime timeout, vendor error, schema mismatch on output | **Tool Call** `status`, error object |
| Planning | Planner cannot satisfy constraints, invalid plan graph | planning step errors, **Execution Plan** metadata |
| Validation | Validator rejects output or missing evidence | `validating` exit with failure |
| Policy | Deny or unmet conditional | policy evaluation with `deny` |
| Timeout | Step or execution SLA exceeded | orchestrator timeout event |

**Recording:** Each failure produces normalized errors on the affected step, **Tool Call**, or execution record; timeline events include type and non-sensitive detail.

**Fail vs continue**

- **Blocking** failures (policy deny on required path, validation failure on mandatory output, unrecoverable tool error on a step that is not **`degraded_allowed`**) → execution transitions to `failed` unless a workflow-specific compensating path is defined and approved.
- **Rule:** A step may be treated as **non-blocking** or allowed to **continue in a degraded manner only if the Execution Plan declares it** (e.g. via `degraded_allowed` or an explicit degraded branch in plan metadata). Ad hoc degradation by the runtime or agents is not permitted.
- **Degraded continuation** must: record **missing evidence** or **reduced completeness** on the **Step Result** and in the **Trace**; **lower confidence** or **trigger validator escalation** (stricter checks, inconclusive marking—Section 10) where platform rules require. The system **must not silently convert a blocking failure into partial success**: terminal `completed` requires explicit satisfaction of validation and policy paths, or an **Execution Plan**-authorized degraded completion path that is itself labeled and auditable (not an implicit downgrade).

## 8. Retry and recovery model

**Safe retries:** **Tool Calls** classified **idempotent** (per **Tool contract**) or read-only with retry-safe semantics, plus retryable vendor errors and transient network failures, within **retry_count** thresholds. Backoff and jitter are applied at the orchestration layer. Each retry attempt appends to the **Trace** (same `step_id`, incremented `retry_count`).

**Unsafe retries:** Steps producing **Action proposals**, **non_idempotent** or **state_changing** effects outside declared keys require explicit policy approval for retry—or fail without automatic retry. **Non_idempotent** **Tool Calls** are not automatically retried (aligned with **Side-effect boundary**, Section 3.6).

**Retry limits:** Per-step ceiling enforced by orchestrator; exceeding limit → step `failed` → execution outcome per Section 7.

**Re-plan conditions:** After certain failure classes (planning deadlock, repeated validation failure suggesting wrong decomposition), orchestrator may transition to `planning` with a new **Execution Plan** revision (`plan_id`, `parent_plan_id`, `revision_reason`), preserving prior revisions in the **Trace**.

**Fallback strategies:** Workflow-defined (e.g. alternate tool, degraded read-only path). Fallback must be declared in **Execution Plan** or policy; ad hoc fallbacks by agents are out of scope for production paths.

## 9. Idempotency and replay

**Execution replay:** Re-running an execution from stored input and a chosen **Execution Plan** revision to support debugging, regression evaluation, or incident analysis. Replay reconstructs the same execution graph, dependency structure, step ordering rules, and **Tool Call** inputs as recorded—or as intentionally varied in **investigative replay** (below).

**Step replay:** Re-executing a single step with frozen inputs and optional frozen retrieval snapshots to isolate defects.

**Why required:** Operations review, compliance evidence, evaluator scoring, and Mukti pattern mining depend on reproducible narratives tied to `execution_id`.

**Structural determinism:** Replay guarantees **structural determinism**: the **Execution Plan** graph, step ordering rules, resolved **Tool Call** inputs (as stored), policy evaluation *inputs* (facts as stored), and **Execution context** (or a declared experimental variant) can be reconstructed for the replay mode in use. **Replay does not guarantee identical LLM or other stochastic model outputs** unless the inference layer pins models, prompts, and seeds per platform policy; those assumptions are recorded in **Trace** metadata when a stricter replay grade is required.

**Exact replay:** Uses the original **Execution Plan** revision, original **Execution context** (or equivalent), and original stored **Tool Call** inputs to reproduce the online shape of the run for audit and regression.

**Investigative replay:** Uses a revised **Execution Plan**, alternate policy or feature flags in a sandbox, or stubbed tools for debugging. Investigative runs are explicitly labeled in metadata so they are not mistaken for exact reproductions of production behavior.

## 10. Validation model

**What validators check:** Schema conformance, evidence sufficiency, prohibited content classes (workflow-specific), consistency with policy-declared output categories, and cross-field sanity (e.g. cited metrics match aggregated numbers).

**When validation runs:** After steps that produce **non-trivial** outputs (declared per workflow), before exposing results to downstream consumers or marking `completed`. High-risk paths may require multiple validator stages.

**Confidence vs validation:** **Confidence** on a **Step Result** is advisory metadata only. **Validation** outcomes override confidence for promotion and completion. High confidence does not imply correctness without passing applicable validation.

**Validator authority (may):**

- Block execution completion until defects are remediated or the execution **fails** per policy.
- **Downgrade confidence** or **mark results as inconclusive** when evidence supports only partial claims.
- **Require re-plan** by failing validation in a way that triggers orchestrator transition to `planning` with a documented `revision_reason`.

**Validator authority (may not):**

- **Execute tools** or initiate **Tool Calls** directly.
- **Override policy decisions**; validators receive policy outcomes as inputs, not vice versa.
- **Mutate execution history** or **Trace**; they emit outcomes that the orchestrator records.

**Effect on output:** Failed validation blocks promotion of outputs; orchestrator may loop to additional steps (if allowed) or fail the execution. Partial or draft outputs are not externally visible unless an explicit, policy-approved “preview” channel exists. Validators are separate from agents; agents do not self-certify.

## 11. Role of Mukti Agent

Mukti operates **only post-execution** (or on snapshot batches), consuming **Traces** and optional operator labels.

- **Inputs:** Frozen **Traces**, feedback signals, and evaluation artifacts—not live step streams mutating state.
- **Analysis:** Identifies failure patterns, planning inefficiencies, validation gaps, and systematic tool issues; clusters recurring policy friction.
- **Outputs:** **Execution Feedback (Mukti)** (Section 3.12) and prioritized suggestions routed to owners; **advisory signals** only.
- **Incorporation:** Recommendations must be **reviewed, validated, or merged through controlled change processes** (e.g. policy rule updates, **Tool contract** changes, validator config) before they influence production workflows. Mukti **does not** directly modify live execution behavior, bypass policy, invoke tools against production without a separate approved release, or perform uncontrolled self-modification of prompts or agents in production.

Separation keeps improvement loops accountable while preserving the integrity of the online runtime.
