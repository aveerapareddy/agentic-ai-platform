# API design

Internal design artifact: how clients and services interact with the Agentic AI Platform at the HTTP/API boundary and across service boundaries. It aligns with the [runtime model](runtime-model.md) and the operational schema in `infra/db/migrations/001_initial_schema.sql`. It is not an OpenAPI spec, routing table, or SDK definition.

## 1. Overview

The API layer exposes **governed execution lifecycle** operations: creating and observing executions, recording approvals, requesting controlled replay, ingesting operator-facing feedback, and retrieving traces for audit and operations. The **api-gateway** is the external ingress; it authenticates, authorizes, shapes errors, and forwards to the **orchestrator** and other backing services as appropriate.

APIs follow the **runtime model** (executions, plans, steps, policy, tools, validation, trace) rather than chat-first patterns because enterprise workflows require stable `execution_id`s, inspectable plans, separable policy decisions, and reproducible narratives. Conversational UX, if present, is built **on top of** these execution APIs inside **operator-console** or approved clients—not as a replacement for them.

## 2. API design principles

| Principle | Implication |
|-----------|-------------|
| **Execution-oriented** | Resources center on `executions` and their artifacts; prompts or model parameters are inputs to steps, not the primary resource model. |
| **Asynchronous by default** | Non-trivial workflows return quickly with an execution in a non-terminal state; clients poll `GET /v1/executions/{id}` or use push notifications where deployed—contract TBD at implementation. |
| **Idempotent creation where possible** | `POST /v1/executions` accepts an idempotency key so duplicate submits do not fork runs (see Section 8). |
| **Explicit status and traceability** | Responses expose `status` consistent with the runtime lifecycle; trace and timeline data are available through dedicated retrieval paths. |
| **Bounded action APIs** | Clients **approve/reject** or **submit feedback**; they do not invoke arbitrary tools or replan executions ad hoc. |
| **Public vs internal** | **External platform APIs** (`/v1/...`) are stable, tenant-scoped, and minimal. **Internal service contracts** are richer, service-to-service, and may evolve under monorepo discipline without exposing every field externally. |

Versioning: external paths use a **major version prefix** (`/v1/`). Breaking changes require a new major version; additive JSON fields are preferred within a major version.

## 3. API surface categories

| Category | Audience | Role |
|----------|----------|------|
| **Execution APIs** | Integrations, operator console | Create execution, read status, list executions. |
| **Approval APIs** | Approvers, operator console | Record decisions that unblock or terminate gated paths. |
| **Replay APIs** | Operators, platform engineers | Request exact or investigative replay in controlled environments. |
| **Feedback APIs** | Operators, feedback pipelines | Submit structured feedback linked to executions (distinct from Mukti’s internal consumption). |
| **Knowledge / retrieval APIs** | Orchestrator-backed clients | Scoped retrieval for humans or services; not a raw vector dump for arbitrary clients. |
| **Internal service APIs** | Services only | Orchestrator ↔ policy-engine, tool-runtime, knowledge-service, feedback-service; Mukti ↔ traces and feedback-service. |

## 4. External platform APIs

Base path: **`/v1`**. All paths below are relative to the gateway. Field names mirror runtime and storage semantics where practical; external responses may project or redact internal fields.

### 4.1 Create execution

**`POST /v1/executions`**

**Purpose:** Start a new execution for a declared `workflow_type` with initial `input` and **execution context** facts (tenant, principal, environment, policy scope).

**Request (pseudo-JSON):**

```json
{
  "workflow_type": "incident_triage",
  "input": { "incident_id": "...", "severity": "high" },
  "context": {
    "tenant_id": "org_123",
    "principal_id": "svc_orchestration",
    "request_id": "req_abc",
    "environment": "prod",
    "policy_scope": "default@2026-03-01",
    "permissions_scope": { "roles": ["incident_reader"] },
    "feature_flags": { "strict_validation": true }
  },
  "idempotency_key": "optional-stable-key"
}
```

**Response (201):**

```json
{
  "execution_id": "uuid",
  "status": "created",
  "workflow_type": "incident_triage",
  "created_at": "ISO-8601",
  "links": { "self": "/v1/executions/{execution_id}" }
}
```

**Rules:** `workflow_type` and `input` must satisfy workflow registration. `context.tenant_id` and `policy_scope` are required for multi-tenant policy. Duplicate `idempotency_key` within retention window returns the **same** `execution_id` (see Section 8).

---

### 4.2 Get execution

**`GET /v1/executions/{execution_id}`**

**Purpose:** Return current execution summary: status, workflow type, timestamps, optional `current_plan_id`, terminal `result` when completed, and lightweight validation summary if present.

**Response (200):**

```json
{
  "execution_id": "uuid",
  "workflow_type": "incident_triage",
  "status": "executing",
  "execution_context_id": "uuid",
  "current_plan_id": "uuid",
  "parent_execution_id": null,
  "input": { },
  "result": null,
  "validation_summary": null,
  "created_at": "...",
  "updated_at": "...",
  "completed_at": null,
  "cancelled_at": null
}
```

**Rules:** Caller must be authorized for the execution’s tenant. Sensitive fields in `input`/`result` may be redacted per policy.

---

### 4.3 List executions

**`GET /v1/executions`**

**Purpose:** Page through executions visible to the caller, with filters (Section 9).

**Query:** `workflow_type`, `status`, `tenant_id` (if caller may scope), `created_after`, `created_before`, `cursor`, `limit`.

**Response (200):**

```json
{
  "items": [ { "execution_id": "uuid", "status": "failed", "workflow_type": "...", "created_at": "..." } ],
  "next_cursor": "opaque-or-null"
}
```

**Rules:** Default ordering: `created_at` descending. Tenant scope is enforced from auth context unless platform admin role explicitly allows cross-tenant listing (implementation-defined).

---

### 4.4 Approve or reject action

**`POST /v1/executions/{execution_id}/approvals`**

**Purpose:** Record an **Approval** tied to an **action proposal** and/or **policy evaluation**, unblocking or rejecting gated work.

**Request:**

```json
{
  "action_proposal_id": "uuid",
  "policy_evaluation_id": "uuid",
  "decision": "approve",
  "approver": "principal_or_role_ref",
  "notes": "optional"
}
```

**Response (201):**

```json
{
  "approval_id": "uuid",
  "execution_id": "uuid",
  "decision": "approve",
  "decided_at": "ISO-8601"
}
```

**Rules:** At least one of `action_proposal_id` or `policy_evaluation_id` must be supplied (matches DB constraint). `decision` ∈ `approve` | `reject` | `defer`. Orchestrator consumes this to transition from `awaiting_approval` when appropriate. **Defer** does not complete the gate; semantics are workflow-defined.

---

### 4.5 Replay execution

**`POST /v1/executions/{execution_id}/replay`**

**Purpose:** Request **exact** or **investigative** replay per runtime model (structural determinism vs stochastic model outputs).

**Request:**

```json
{
  "mode": "exact",
  "plan_id": "uuid",
  "environment_target": "sandbox",
  "label": "post-incident-review"
}
```

**Response (202):**

```json
{
  "replay_execution_id": "uuid",
  "source_execution_id": "uuid",
  "status": "created",
  "mode": "exact"
}
```

**Rules:** Replay may be denied if policy forbids cloning to `environment_target` or if source lacks sufficient trace completeness. **Investigative** mode must be labeled in stored metadata; response should echo `mode`. New execution is typically a child or linked run (`parent_execution_id` or metadata link—implementation choice).

---

### 4.6 Submit execution feedback

**`POST /v1/executions/{execution_id}/feedback`**

**Purpose:** Ingest **operator or integration feedback** about a run (labels, corrections, qualitative signals). Distinct from **Execution Feedback (Mukti)** produced by **mukti-agent**; this endpoint supports human-in-the-loop and external ticketing alignment.

**Request:**

```json
{
  "source": "operator_console",
  "labels": ["false_positive_root_cause"],
  "detail": { "comment": "..." },
  "source_scope": null
}
```

**Response (201):**

```json
{
  "feedback_record_id": "uuid",
  "execution_id": "uuid",
  "created_at": "ISO-8601"
}
```

**Rules:** Stored in **feedback-service** (or equivalent); may feed Mukti batches asynchronously. Does not mutate execution status by itself.

---

### 4.7 Get execution trace

**`GET /v1/executions/{execution_id}/trace`**

**Purpose:** Return a **materialized trace view** for operators: steps, step results (summarized), tool calls, policy evaluations, approvals, optional timeline events, and plan revision pointers—reconstructed from normalized storage.

**Response (200):**

```json
{
  "execution_id": "uuid",
  "execution_context": { "tenant_id": "...", "environment": "prod" },
  "plans": [ { "plan_id": "uuid", "plan_version": 1, "parent_plan_id": null } ],
  "steps": [ ],
  "tool_calls": [ ],
  "policy_evaluations": [ ],
  "approvals": [ ],
  "timeline": [ ]
}
```

**Rules:** Large payloads may support **cursor-based** sub-resources in implementation (e.g. `.../trace/steps`); this document defines the conceptual aggregate. Redaction applies to secrets and PII in `tool_calls.output` and `step_results`.

## 5. Internal service contracts

Architectural message shapes (not transport-specific). Services authenticate with mTLS or internal identity as deployment policy dictates.

| Caller | Callee | Contract (conceptual) |
|--------|--------|------------------------|
| **api-gateway** | **orchestrator** | Start execution, get status, list (proxied queries), submit approval, request replay, fetch trace projection. |
| **orchestrator** | **policy-engine** | Evaluate proposal or tool path: send **Execution context**, `subject_ref`, tool **side_effect_class** / **idempotency** snapshot; receive **decision**, `reason`, `evaluated_rules`. |
| **orchestrator** | **tool-runtime** | Execute **Tool Call**: `tool_name`, validated `input`, `execution_id`, `step_id`, `execution_context_id`, optional `action_proposal_id`; receive `output`, `status`, `latency_ms`, `error`. |
| **orchestrator** | **knowledge-service** | Retrieval requests scoped by tenant and workflow; return cited chunks / pointers for **Step Result** `evidence` (traceable). |
| **orchestrator** | **feedback-service** | Persist operator feedback events; optional notify downstream consumers. |
| **feedback-service** | **mukti-agent** | Deliver batches or pointers to frozen traces and operator labels for **Execution Feedback (Mukti)** generation; Mukti writes advisory records, not live execution mutations. |
| **mukti-agent** | Storage / **feedback-service** | Write `execution_feedback` rows (failure_types, patterns_detected, improvement_suggestions); no direct **orchestrator** control channel. |

Internal APIs may expose step-level transitions, plan revision creation, and validator callbacks that are **not** mirrored on the public `/v1` surface.

## 6. Execution status model

Statuses match the runtime lifecycle:

| Status | Terminal? | Client interpretation |
|--------|-----------|------------------------|
| `created` | No | Accepted; orchestration may not have started planning. |
| `planning` | No | **Execution Plan** revision in progress. |
| `executing` | No | Steps scheduling/running; tool and agent work occurs here. |
| `validating` | No | Validators running on non-trivial outputs. |
| `awaiting_approval` | No | Gated on human or system approval per policy. |
| `completed` | **Yes** | Success path; `result` populated per workflow rules. |
| `failed` | **Yes** | Blocking failure; see `result` / trace for cause. |
| `cancelled` | **Yes** | Operator or caller cancellation. |

**Terminal states** (`completed`, `failed`, `cancelled`) do not transition further. Clients should not assume prompt delivery of terminal state for long runs; use polling or notifications.

## 7. Error model

Platform errors use a consistent envelope (conceptual):

```json
{
  "error": {
    "code": "POLICY_DENIED",
    "message": "Human-readable, safe for operators",
    "details": { },
    "request_id": "correlation-id",
    "execution_id": "uuid-if-applicable"
  }
}
```

| Code (example) | Meaning | HTTP (typical) |
|----------------|---------|----------------|
| `VALIDATION_ERROR` | Request body or query invalid vs published contract | 400 |
| `AUTHORIZATION_ERROR` | Authenticated but not allowed for tenant/resource | 403 |
| `POLICY_DENIAL` | Policy engine denied proposed action or transition | 409 or 422 (policy-specific) |
| `NOT_FOUND` | Unknown `execution_id` or sub-resource | 404 |
| `CONFLICT` | State conflict (e.g. approval on wrong proposal state, idempotency mismatch) | 409 |
| `TRANSIENT_DEPENDENCY_FAILURE` | Downstream unavailable; safe to retry | 503 |
| `EXECUTION_FAILED` | Execution already terminal `failed` when operation requires active run | 409 |
| `REPLAY_NOT_ALLOWED` | Replay forbidden by policy or incomplete trace | 403 or 422 |

**API failure** vs **workflow failure:** An **API failure** means the HTTP request did not achieve its protocol goal (validation, auth, not found). **Workflow failure** means the execution reached `failed` legitimately; `GET` execution may return **200** with `status: "failed"`. Do not conflate `500` with a bad business outcome inside an execution.

## 8. Idempotency and concurrency

- **Create execution:** `Idempotency-Key` header or `idempotency_key` body field; scope is `(tenant_id, workflow_type, key)` or stricter per deployment. Conflicting payload with same key → **409 CONFLICT**.
- **Replay:** Subject to policy; duplicate replay requests may return existing `replay_execution_id` if idempotent replay submission is supported.
- **Approvals:** Optimistic concurrency: if proposal already `approved`/`rejected`/`executed`, second conflicting POST returns **409** with `CONFLICT`. `defer` may allow multiple records—workflow rules define whether multiple deferrals are valid.
- **Trace read:** Read-only; no concurrency concerns beyond cache freshness.

## 9. Pagination, filtering, and retrieval

**List executions**

- **Filters:** `workflow_type` (exact), `status` (single or small set), `tenant_id` (when caller has multi-tenant scope), `created_after` / `created_before` (ISO-8601, half-open intervals).
- **Pagination:** Cursor-based preferred (`cursor` + `limit`); opaque cursor encodes sort key. Offset pagination discouraged at scale.
- **Ordering:** Default `created_at DESC`. Optional `sort=created_at:asc` if product needs it.

**Trace:** If aggregate too large, implementations may cap embedded arrays and provide `next_cursor` per section or separate sub-resources—documented in gateway at implementation time.

## 10. Security and access boundaries

- **Authenticated callers:** All `/v1` routes require authentication (tokens, mTLS, or platform IAM integration—deployment-specific).
- **Tenant scoping:** Every request is evaluated against `tenant_id` from token or explicit allowed scope; list and get enforce isolation.
- **Role-based access:** Roles distinguish operator read, approval authority, replay in sandbox, and admin diagnostics.
- **Restricted actions:** `POST .../approvals`, `POST .../replay`, and `POST .../feedback` require elevated or workflow-specific roles.
- **Tools not exposed to clients:** **tool-runtime** is reachable only from **orchestrator** (internal). Clients never POST arbitrary tool invocations; actions flow through executions, proposals, policy, and approvals. This preserves auditability and **side-effect boundary** from the runtime model.

Rate limits and quotas are enforced at the **api-gateway**; numeric limits are deployment configuration, not part of this document.

## 11. Non-goals

The public platform API is **not**:

- A **generic chat completion** or prompt-completion endpoint.
- **Direct tool access** for arbitrary clients to run registered tools.
- An **unbounded agent control** interface (no ad hoc replan, skip validation, or bypass policy through the gateway).
- A replacement for **internal** observability pipelines (metrics/traces to monitoring systems remain separate concerns).

---

## Summary (for implementers)

**Endpoints defined (conceptual):** `POST/GET /v1/executions`, `GET /v1/executions` (list), `POST .../approvals`, `POST .../replay`, `POST .../feedback`, `GET .../trace`.

**Internal contracts:** Gateway→orchestrator; orchestrator→policy-engine, tool-runtime, knowledge-service, feedback-service; feedback-service↔mukti-agent; Mukti→storage/feedback persistence.

**Assumptions left open:** Exact HTTP status mapping for every policy outcome; push notification contract; OpenAPI publication; maximum trace page size; idempotency retention TTL; whether `feedback_record_id` equals a DB row in `execution_feedback` or a separate operator-feedback table; child vs sibling linkage for replay executions.
