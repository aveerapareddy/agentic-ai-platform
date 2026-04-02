# System overview

Situate the Agentic AI Platform in its enterprise context: governed multi-agent execution over internal systems, with explicit lifecycle, policy, validation, and post-execution improvement. This page summarizes subsystems and trust boundaries at a glance; execution semantics live in the [runtime model](runtime-model.md), and HTTP shape in [API design](api-design.md).

## Context diagram

The platform sits between **enterprise clients** (ticketing, cloud control planes, cost APIs, identity) and **operators** who observe traces, approve actions, and submit feedback. Inbound traffic enters through **api-gateway**; work is coordinated by **orchestrator** with **policy-engine** and **tool-runtime** enforcing side effects. **knowledge-service** supplies traceable retrieval. **feedback-service** and **mukti-agent** consume completed work for improvement signals. **operator-console** is a first-party UI over the same platform APIs—not a separate control plane.

## Major subsystems

| Subsystem | Role |
|-----------|------|
| **Ingress and API** | **api-gateway**: authentication, routing, rate limits, stable `/v1` surface. |
| **Control runtime** | **orchestrator**: execution lifecycle, plans, steps, validation gates, calls to policy, tools, knowledge. |
| **Governance** | **policy-engine**: allow/deny/conditional decisions; no tool execution. |
| **Execution surface** | **tool-runtime**: registered tools only; auditable **Tool Calls**. |
| **Retrieval** | **knowledge-service**: indexed and queryable knowledge with citations for steps. |
| **Feedback loop** | **feedback-service**: operator and integration feedback; handoff to Mukti. |
| **Improvement** | **mukti-agent**: post-execution analysis; advisory output only. |
| **Operations UI** | **operator-console**: executions, traces, approvals—via gateway. |

## External dependencies

Typical dependencies (exact vendors are deployment choices): identity and access management, observability backends (metrics, logs, traces), secret stores, message or job infrastructure where async work is used, LLM or inference endpoints invoked **inside** bounded agent steps—not as a public chat API. Data stores back execution and trace persistence; schema direction is in `infra/db/migrations/`.

## Trust boundaries

- **Public / partner** callers see only **api-gateway** and published contracts.
- **Internal services** trust network identity and platform-issued context; they must not accept unauthenticated tool or policy calls from the internet.
- **Tools** run with service credentials scoped per registration; clients never hold tool credentials.
- **Mukti** reads stored traces and feedback; it does not receive live execution control messages.

---

## Service Responsibilities and Interaction Model

### 1. Purpose

Service boundaries keep **policy evaluation**, **tool execution**, **retrieval**, and **post-execution analysis** separable so each can be scaled, secured, and owned independently. A single generic backend would collapse those concerns, encourage implicit prompting paths, and make audit (“who decided, who acted”) harder to prove.

The platform is **not** one monolith: the **orchestrator** coordinates but does not subsume policy logic, tool implementations, or Mukti’s batch analysis.

### 2. Service ownership model

#### api-gateway

| | |
|--|--|
| **Primary responsibility** | External HTTP ingress: authn/authz hooks, routing, request validation, error shaping, rate limits. |
| **Owns** | Route definitions, client-facing API version mapping, gateway-level caching policy (if any). |
| **Must not own** | Execution state, planning logic, policy rules, or tool implementations. |
| **Reads/writes** | Minimal session or rate-limit state; forwards bodies; does not author execution rows. |
| **Callers** | External clients, **operator-console**. |

#### orchestrator

| | |
|--|--|
| **Primary responsibility** | Drive **Execution** lifecycle: plans, steps, retries, validation orchestration, correlation with **Execution context**. |
| **Owns** | Workflow scheduling rules, step state transitions, when to call policy, tools, knowledge, and persistence of execution graph (as system of record for runs). |
| **Must not own** | Policy rule definitions, tool code, vector indexes, or Mukti models. |
| **Reads/writes** | Executions, plans, steps, step results, links to policy/tool/approval records; timeline materialization. |
| **Callers** | **api-gateway**, internal batch or admin paths (if any). |

#### policy-engine

| | |
|--|--|
| **Primary responsibility** | Evaluate requests: return **allow**, **deny**, or **conditional** with reasons and evaluated rule references. |
| **Owns** | Policy evaluation records, rule pack versioning surface (storage may be shared DB). |
| **Must not own** | Tool execution, step planning, or execution state transitions. |
| **Reads/writes** | Evaluation inputs/outputs; may read policy configuration stores. |
| **Callers** | **orchestrator** only (not clients). |

#### tool-runtime

| | |
|--|--|
| **Primary responsibility** | Execute **Tool Calls** for registered tools: validate inputs, enforce timeouts, return outputs or structured errors. |
| **Owns** | Tool worker processes, connection pools to external systems, per-tool quotas. |
| **Must not own** | Execution plan graph, policy decisions, or direct mutation of “workflow completed” without orchestrator. |
| **Reads/writes** | **Tool Call** audit rows; side effects on external systems per tool contract. |
| **Callers** | **orchestrator** only. |

#### knowledge-service

| | |
|--|--|
| **Primary responsibility** | Retrieval over corpora with tenant and workflow-aware access; return citable chunks for **Step Result** evidence. |
| **Owns** | Indexes, embedding pipelines (if used), retrieval APIs—not the orchestrator’s step scheduler. |
| **Must not own** | Execution lifecycle or policy decisions. |
| **Reads/writes** | Knowledge artifacts and indexes; optional query logs. |
| **Callers** | **orchestrator**; optionally read-only internal analytics (deployment-defined). |

#### feedback-service

| | |
|--|--|
| **Primary responsibility** | Ingest operator and integration feedback tied to executions; expose data for Mukti and reporting. |
| **Owns** | Feedback ingestion contracts, retention, routing to consumers. |
| **Must not own** | Live execution transitions or policy rules. |
| **Reads/writes** | Operator feedback records; handoff queues or topics for **mukti-agent**. |
| **Callers** | **api-gateway** (via orchestrator or dedicated internal path per API design), **mukti-agent** for reads. |

#### mukti-agent

| | |
|--|--|
| **Primary responsibility** | Post-execution analysis: patterns, failure classes, improvement suggestions (**Execution Feedback (Mukti)**). |
| **Owns** | Analysis jobs, model/prompt config for analysis (not production agent prompts). |
| **Must not own** | Running executions, tool invocation in production paths, or policy mutation without a governed release process. |
| **Reads/writes** | Reads traces and feedback; writes advisory **execution_feedback** (or equivalent) records. |
| **Callers** | **feedback-service** or scheduled workers; not the browser. |

#### operator-console

| | |
|--|--|
| **Primary responsibility** | UI for operators: list/get executions, trace views, approval actions, feedback submission. |
| **Owns** | Frontend assets, client-side state, console-specific feature flags. |
| **Must not own** | Backend execution or tool credentials. |
| **Reads/writes** | None server-side except through **api-gateway**. |
| **Callers** | Human operators (browser). Calls **api-gateway** only. |

### 3. Interaction boundaries

**Allowed**

| From | To | Nature |
|------|-----|--------|
| **api-gateway** | **orchestrator** | Start and observe executions, approvals, replay, trace reads, feedback submission (as per [API design](api-design.md)). |
| **orchestrator** | **policy-engine** | Policy evaluation requests for proposals, tool paths, transitions. |
| **orchestrator** | **tool-runtime** | **Tool Call** execution after policy/approval gates per runtime model. |
| **orchestrator** | **knowledge-service** | Scoped retrieval for steps. |
| **orchestrator** | **feedback-service** | Persist operator feedback events. |
| **feedback-service** | **mukti-agent** | Deliver batches or notifications for analysis. |
| **operator-console** | **api-gateway** | All server communication. |

**Disallowed or discouraged**

| Pattern | Why |
|---------|-----|
| **operator-console** → **tool-runtime** (or any internal service except gateway) | Bypasses auth, tenant enforcement, and audit aggregation at the gateway/orchestrator. |
| **mukti-agent** → **orchestrator** “control” APIs | Mukti is post-execution; must not drive live step execution or replan. |
| **policy-engine** → **tool-runtime** | Policy decides; it does not act. |
| **Tools** → **orchestrator** internal “skip validation” hooks | Violates explicit execution and validation separation; state changes go through orchestrator contracts only. |
| **Clients** → **policy-engine** / **knowledge-service** directly | Breaks trust boundary and duplicates gateway policy. |

### 4. Sync vs async boundaries

| Interaction | Expected pattern |
|-------------|------------------|
| **Gateway → orchestrator** (create execution, get execution, list) | **Synchronous** request/response; create may return before terminal completion. |
| **Orchestrator → policy-engine** | **Synchronous** for gating decisions on the hot path; timeouts bounded. |
| **Orchestrator → tool-runtime** | **Synchronous** per **Tool Call** with strict timeouts; long tools may use internal async + polling pattern inside tool-runtime without exposing that to clients. |
| **Orchestrator → knowledge-service** | Usually **synchronous** for step-bound retrieval; heavy indexing is async behind the service. |
| **Orchestrator → feedback-service** | **Synchronous** acknowledge of accepted feedback; downstream fan-out **asynchronous**. |
| **Feedback-service → mukti-agent** | **Asynchronous** (queue, job, or scheduled pull); Mukti does not block execution completion. |
| **Operator-console → gateway** | **Synchronous** HTTP; UI may poll or subscribe per product decision. |

### 5. Data ownership and persistence boundaries

| Concern | System of record (logical) | Notes |
|---------|----------------------------|--------|
| **Execution state** | **orchestrator** (persisted in shared operational DB) | Plans, steps, step results, execution status, `current_plan_id`. |
| **Policy decisions** | **policy-engine** authorship; **orchestrator** stores evaluation rows for trace | Evaluations are immutable facts on the trace. |
| **Tool call records** | **tool-runtime** produces outcomes; storage often co-located with orchestrator DB for trace joins | Same PostgreSQL instance is acceptable; **logical** owner for semantics is tool-runtime for execution accuracy, platform for retention. |
| **Knowledge artifacts** | **knowledge-service** | Indexes and source metadata; not the execution DB. |
| **Operator feedback** | **feedback-service** (or tables delegated to same DB with clear ownership) | Distinct from Mukti output if schema split in implementation. |
| **Execution feedback (Mukti)** | **mukti-agent** writes advisory rows | Read by operators and change processes; no feedback loop into live runs without governance. |

Shared database: a single PostgreSQL cluster may host multiple logical domains; **ownership** is by service contract, not only by schema file name.

### 6. Failure isolation

| Failure | Expected containment |
|---------|----------------------|
| **tool-runtime** | Failing **Tool Call** marks call/step failed per runtime rules; orchestrator may retry, degrade, or fail execution without taking down other tools or policy. |
| **policy-engine** | Unavailable: orchestrator treats as **transient dependency failure**—executions block gated transitions or fail safe (deny) per configuration; other read-only paths may continue only if policy allows. |
| **knowledge-service** degradation | Steps requiring retrieval may fail or follow plan-declared degradation; unrelated steps continue if dependencies permit. |
| **mukti-agent** | Analysis backlog grows; **no impact** on running executions. Operator feedback ingestion should still succeed without Mukti. |
| **operator-console** | UI unavailable; **executions continue**; integrations via gateway still function if gateway and orchestrator are healthy. |

### 7. Scaling considerations

| Service | Scale drivers |
|---------|----------------|
| **api-gateway** | Request volume, TLS/auth overhead, WAF/gateway rules. |
| **orchestrator** | Concurrent **executions** and steps, state DB write throughput, validation fan-out. |
| **policy-engine** | Evaluations per second, rule complexity, cold start of policy bundles. |
| **tool-runtime** | Concurrent **Tool Calls**, external API rate limits, tail latency. |
| **knowledge-service** | Query QPS, index size, embedding/reindex batch load. |
| **feedback-service** | Write rate of feedback events, fan-out to Mukti. |
| **mukti-agent** | Batch and trace analysis volume, model inference cost—not tied to online QPS. |
| **operator-console** | Static asset CDN; API load is subset of gateway traffic. |

### 8. Non-goals

This architecture document does **not** specify:

- **Service mesh** configuration, sidecar policies, or per-route circuit-breaker matrices.
- **Multi-region** failover, data residency partitioning, or global load balancing.
- **Direct browser or partner access** to **orchestrator**, **policy-engine**, **tool-runtime**, or **knowledge-service**.

Those belong in later infrastructure ADRs and runbooks when deployment targets are fixed.

---

### Summary for readers

**Responsibilities clarified:** Each of the eight services has an explicit primary role, ownership boundary, persistence touchpoints, and allowed callers.

**Interaction rules added:** Allowed call graph (gateway/orchestrator hub, policy and tools internal-only, feedback → Mukti async); explicit disallow list for console→tool, Mukti→live control, policy→tools, client→internals.

**Left open:** Whether feedback from `POST .../feedback` lands in the same store as Mukti `execution_feedback`; exact async transport (queue vs poll); gateway-to-orchestrator vs gateway-to-feedback path for feedback; multi-DB vs single shared instance per environment.
