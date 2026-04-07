# Project End State

One-line purpose: Define the target production-grade **internal platform and product surface** this repository is building toward, what “complete” means, how it differs from thin AI wrappers, and what each implementation phase must deliver.

This document complements [project-constitution.md](project-constitution.md), [runtime-model.md](../architecture/runtime-model.md), [system-overview.md](../architecture/system-overview.md), and [api-design.md](../architecture/api-design.md). It does not replace them. **Scope:** platform capabilities through **Phase 7** plus a **Phase 8 — Product Layer** (gateway, operator console, evaluation, Mukti v2, replay, and two first-class workflows) so completion criteria include operable ingress and UI, not only library or CLI demos.

---

## 1. System Definition

The Agentic AI Platform is:

- A **governed multi-agent execution platform**: work is expressed as durable **executions**, versioned **plans**, and **steps** with explicit lifecycle and trace correlation—not as ad hoc model turns.
- A **control plane** over models, **registered tools**, and **enterprise systems**: side effects and high-risk actions are mediated by a **policy-engine** and **tool-runtime**, not by model output alone.
- A system with **explicit execution semantics**: scheduling, state transitions, validation gates, and replay are defined by the platform and stored as data. Prompts may inform step outputs; they do not define the control graph.

The system is **not**:

- A **chatbot** or conversational surface as the primary execution primitive.
- A **prompt wrapper** where behavior is reconstructed only from prompt text and model replies.
- A **framework-assembled demo** where LangChain, LangGraph, or similar products define lifecycle, state, or governance.
- A **generic RAG application** where retrieval and chat are the product; here retrieval is a bounded service feeding **evidence** into governed steps, not an end-to-end “ask the corpus” loop without execution semantics.
- An **uncontrolled autonomous agent** that plans, acts, and mutates systems without policy gates, tool registration, and auditable records.

---

## 2. End-State Capabilities

### 2.1 Execution System

- **Durable execution model**: Stable identifiers (**execution**, **execution context**, **plan** revisions, **steps**) persisted in relational storage as the system of record.
- **Step-based workflows**: Product workflows map to the same step abstraction; agents operate *within* steps; tools are invoked as auditable **tool calls** via the tool runtime.
- **Explicit state machine**: Execution and step statuses transition only through defined rules; the control layer remains deterministic and inspectable (runtime model).
- **Replay support**: Structure and inputs can be reproduced for review and debugging; replay modes distinguish exact reproduction from investigative variants where documented ([api-design.md](../architecture/api-design.md) replay category).
- **Partial failure handling**: Retries, degraded paths, and explicit failure classification are recorded; silent degradation without trace is excluded.
- **Validation before completion**: No execution reaches a terminal success state without an explicit validation phase and recorded validation outcome (constitution §6.1).

### 2.2 Governance and Control

- **Policy-engine enforcing decisions**: Allow / deny / conditional outcomes with reasons and evaluated rule references; evaluation is independent of agent prompt content.
- **Action proposal lifecycle**: State-changing work is represented as proposals with risk and approval attributes; agents do not execute side effects directly.
- **Approval flow for high-risk actions**: Human decisions persisted and attributable; linked to executions and policy evaluations in the trace.
- **Auditable decisions**: Policy evaluations and approvals are queryable records, not inferred from transcripts.

### 2.3 Tool Integration

- **Tool-runtime with registered tools**: Only named, registered tools execute under orchestrator coordination.
- **Typed contracts**: Inputs, outputs, side-effect class, idempotency; violations are structured errors.
- **Controlled side effects**: Mutations after policy (and approval when required); orchestrator does not embed tool implementations.
- **Execution audit for every tool call**: Each invocation is a durable **tool call** row tied to execution, step, and context.

### 2.4 Knowledge and Retrieval

- **Knowledge-service with traceable retrieval**: Tenant- and workflow-scoped retrieval APIs suitable for binding into **step results**.
- **Evidence attached to step results**: Citations, pointers, or excerpts where workflow rules require grounding; gaps explicit in trace.
- **Separation of execution data and knowledge data**: Execution graph in relational execution stores; indexes and corpora owned by knowledge-service (constitution §5.2).

### 2.5 Feedback and Improvement

- **Feedback-service capturing operator input**: Structured feedback linked to executions; contracts distinct from Mukti’s internal consumption where API design separates them.
- **Mukti-agent performing post-execution analysis**: Reads traces and feedback; writes structured **execution feedback**.
- **Pattern detection and improvement suggestions**: Advisory output for humans and release processes.
- **No direct mutation of live execution behavior**: Changes ship via configuration, rule packs, and code—not runtime self-modification from Mukti (constitution §6.3).

### 2.6 Observability

- **Full execution trace**: Timeline plus normalized rows (executions, steps, step results, tool calls, policy evaluations, approvals, validation) sufficient to reconstruct ordering and decisions.
- **Step-level visibility**: Status, results, errors, latency without relying on raw model logs alone.
- **Policy and tool call visibility**: First-class records in storage and API projections where applicable.
- **Ability to reconstruct any execution**: Historical review does not require external systems to be online for the stored narrative.

### 2.7 Access and Product Surface

- **API gateway as unified ingress**: Single external HTTP entry for platform operations aligned with [api-design.md](../architecture/api-design.md): **authentication hooks** (identity integration as deployment attaches), **request validation** and error shaping at the boundary, **routing** to **orchestrator** (and other backing paths only where API design permits, e.g. feedback)—not ad hoc client access to internal services.
- **Operator-console as first-class product surface**: Browser UI used by operators for **execution exploration** (list, filter, detail), **trace inspection** (steps, tool calls, policy, approvals, timeline projections), **approval handling** for gated paths, and **feedback submission**—calling **api-gateway** only (per [system-overview.md](../architecture/system-overview.md) trust boundaries).
- **Separation of platform services and product-facing interfaces**: **Orchestrator**, **policy-engine**, **tool-runtime**, **knowledge-service**, **feedback-service**, **mukti-agent**, and **evaluation-engine** (§4) implement domain behavior and persistence; **api-gateway** and **operator-console** expose controlled, versioned access and UX. Critical logic and side effects do not move into the UI or gateway beyond ingress, validation, and forwarding.

### 2.8 Evaluation and Metrics

- **Execution-level metrics** (derived from stored execution and trace data, not from undocumented side channels):
  - **Model fallback rate**: share of step-level model invocations that recorded deterministic fallback vs model-runtime path (per trace events / step semantics in storage).
  - **Validation success rate**: outcomes of validation phase / validation-bearing steps as persisted.
  - **Policy deny / conditional rate**: counts or rates of **deny** vs **conditional** vs **allow** outcomes where **policy_evaluations** exist.
  - **Tool success rate**: tool call completion vs structured failure as recorded in **tool_calls** (and step linkage).
  - **Latency per step**: end-to-end step duration as recorded or computable from step timestamps in the execution graph.
- **Aggregation dimensions** (for reporting and regression detection): **workflow** (`workflow_type`), **step type** / planner step name, **tool** name, **policy rule** / evaluated rule references where stored.
- **Evaluation outputs**: **`evaluation_score`** (workflow- or bundle-defined scalar or structured score from defined formulas), **anomaly signals** (statistical or rule-based flags over aggregates), **degradation indicators** (threshold breaches on the metrics above).
- **Trace-grounded evaluation only**: Metrics and scores are **computed from persisted execution, step, result, tool, policy, and timeline data**. There are **no hidden model or platform metrics** that matter for product evaluation but exist only outside the trace and stored artifacts (constitution §4.1, §5.3).

### 2.9 Replay and Debugging

- **Replay capability**:
  - **Exact replay**: same stored inputs and execution structure drive a new run (or re-materialized narrative) in a controlled target environment; stochastic model outputs may differ where documented in the runtime model, but **platform-stored** structure and inputs are authoritative ([api-design.md](../architecture/api-design.md) replay category).
  - **Investigative replay**: replay with **modified inputs** or labels for hypothesis testing; mode and deltas must be **persisted and inspectable** so reviews do not confuse investigative runs with production-faithful copies.
- **Requirement**: Replay **uses stored execution structure** (plans, steps, context snapshots as defined for replay); **differences** between source and child or investigative runs must be **inspectable** (metadata, linked `replay_execution_id`, mode flags).
- **Debugging**: Operators and engineers can compare runs **step-by-step** and at **trace** granularity (timeline, tool calls, policy evaluations, validation) without depending on ephemeral application logs as the sole source of truth.

### 2.10 Cross-Execution Insights (Mukti v2)

- **Evolution**: **Mukti** extends beyond **per-execution** analysis (Phase 6) to **cross-execution** analysis over batches of stored traces and feedback: **pattern detection** across runs, **failure clustering**, and **instability identification** (e.g. recurring step/tool/policy failure modes).
- **Outputs**: **Top failure types**, **recurring patterns** (structured, queryable), **ranked improvement suggestions** for humans and release processes—still **advisory**.
- **Constraints** (unchanged in spirit from constitution §6.2–6.3): **Post-execution only**; **no control-plane mutation** (no live execution transitions, no policy/tool/plan changes from Mukti output without a governed release); **advisory output only** written to durable feedback or insight records, not silent runtime behavior changes.

---

## 3. Core Workflows

**Minimum product requirement:** At least **two** workflows must be **fully implemented** (end-to-end verticals with workflow-specific planners, tools and/or retrieval as required, validation, and trace—not scaffold-only generic plans): **incident triage** and **cost attribution and analysis**. The system must demonstrate **multi-workflow reuse** of the **same** execution model (executions, plans, steps, trace, policy, and tools as applicable). Those two workflows must **exercise different platform capabilities** (e.g. distinct tool sets, retrieval usage, validation semantics, or governance paths)—not the same scenario duplicated under another name.

The following workflows must be **implemented and demonstrated** end to end (the two named above as **first-class** verticals; others as specified in §5).

| Workflow | Role |
|----------|------|
| **Incident triage** | Structured triage and root-cause support; bounded reads/writes via tools where policy allows. |
| **Cost attribution and analysis** | Cross-system cost and usage reasoning; retrieval-backed evidence where required; auditable access to cost data via tools. |
| **Policy-aware execution** | Exercises deny/conditional policy, proposals, and approvals on the hot path—not only happy-path allows. |
| **Feedback-driven improvement loop (Mukti)** | Feedback ingestion feeds analysis; Mukti emits structured feedback from traces without mutating in-flight runs. |

For **each** workflow:

- It must use the **common execution model** (same execution, context, plan, step, and trace concepts as in the runtime model).
- It must **exercise multiple platform components** (at minimum orchestrator + policy + tools for governed paths; knowledge and/or feedback + Mukti where the workflow definition requires them).
- It must produce **traceable outputs** (durable steps, results, and relevant policy/tool/validation records—not only free text).
- It must demonstrate **realistic control and validation behavior** (including at least one scenario per workflow class where policy or validation materially affects the outcome).

---

## 4. System Components

| Component | Purpose | Expected depth |
|-----------|---------|----------------|
| **api-gateway** | **Required for product completeness**: unified HTTP ingress—authn/authz hooks, routing, request validation, rate limits, `/v1` mapping per [api-design.md](../architecture/api-design.md); forwards to orchestrator (and other allowed backing paths). Does not own execution or policy logic. | **Medium**: **real** routing and validation behavior in a single-environment deployment—not a placeholder directory; not a full global edge or full enterprise IAM product. |
| **orchestrator** | Execution lifecycle, plan/step scheduling, calls to policy, tool-runtime, knowledge; persistence of execution graph; validation orchestration. | **Deep**: platform core. |
| **policy-engine** | Allow/deny/conditional evaluation, reasons, rule references; no tool execution. | **Deep**: real evaluations and stored records. |
| **tool-runtime** | Registered tools only; contracts, timeouts, structured errors; durable tool calls. | **Medium**: **small** set of tools, **full** depth per tool (audit, idempotency, side-effect class). |
| **knowledge-service** | Scoped retrieval; citable chunks for step evidence. | **Medium**: representative corpora and APIs. |
| **feedback-service** | Ingest and expose feedback tied to executions for Mukti and reporting. | **Minimal but real**: durable rows and stable contracts. |
| **mukti-agent** | Post-execution analysis; structured execution feedback; **Mukti v2** cross-execution insights (§2.10) within same service boundary or logical module. | **Medium**: reliable batch jobs; strict non-control-plane boundary. |
| **evaluation-engine** | Computes execution metrics and aggregates (§2.8) from stored trace data; exposes evaluation results for insights, gateway metrics endpoints, and operator-console views. | **Medium**: derived metrics and query APIs (or gateway-proxied reads); **no** separate data warehouse required for the scoped end-state. |
| **operator-console** | **Required minimal but real UI**: first-party product surface over **api-gateway**—**execution listing** (with filter/search as API supports), **execution detail**, **trace viewing** (steps, tools, policy, approvals, timeline), **approvals** actions, feedback submission, and surfaces for **evaluation** / **Mukti v2** insights as data is exposed by APIs. | **Minimal but real**: functional operator tasks without a productized UX program or full design system. |

---

## 5. What “Complete” Means

The system is considered **complete** for this program when:

- Execution flows run **end-to-end** through **orchestrator**, **policy-engine**, and **tool-runtime** (knowledge-service where the workflow requires retrieval).
- **Execution state** is **persisted** and **replayable** per the runtime model; trace narrative is not reconstructed only from application logs.
- **Validation is enforced** before any **completed** success terminal state; outcomes are stored and inspectable.
- **At least two major workflows** from §3 are **fully demonstrated** with **realistic inputs and outputs** (structured step results, not placeholder-only content). **Incident triage** and **cost attribution and analysis** are both **required** as fully implemented verticals (§3). At least one path **explicitly** exercises policy/approval (deny, conditional, or approval-gated success)—within those workflows or as a clearly linked scenario. *Assumption:* “policy-aware execution” and “feedback-driven improvement loop” remain cross-cutting expectations as in §3’s per-workflow criteria.
- **Traces** are **inspectable** and **meaningful** via APIs or operator-console paths aligned with api-design trace/execution categories.
- **Policy and approval paths** are **exercised** (including at least one deny or approval-gated success path).
- **Mukti** produces **structured feedback** from stored traces (and feedback-service where applicable) without altering live execution behavior; **Mukti v2** cross-execution insights (§2.10) are **produced and queryable** where Phase 8 applies.
- **No critical logic** depends on **hidden prompt behavior**; prompts operate inside bounded steps; policy and state live in data and services.
- **Service boundaries remain intact**: orchestrator does not implement policy rules, tool bodies, or retrieval indexes; constitution §8.2 holds in code review.
- The result is **credible as an internal platform** (operators and engineers can extend it) **not** a one-off demo application.
- The system exposes an **API surface via api-gateway** for **executions**, **traces**, **approvals**, **replay**, and **metrics/evaluation** results (per §2.7–2.8 and [api-design.md](../architecture/api-design.md); metrics routes may be added as documented extensions to the `/v1` surface).
- **Operator-console** enables **viewing executions**, **inspecting traces**, **handling approvals**, and accessing **evaluation and Mukti v2** views as APIs provide data.
- **At least one workflow** is **operable end-to-end through the UI or gateway** (create/observe complete path), **not** only via in-process CLI or test harness.
- **Evaluation metrics** are **computed and queryable** (§2.8)—not merely implied by raw tables without aggregation or API.
- **Replay capability** exists (**API or CLI**): at least **one** **demonstrated** replay (exact or investigative) with inspectable linkage to source execution data.
- **Two workflows** (**incident triage** and **cost attribution and analysis**) are **implemented and demonstrated** as distinct verticals per §3.

---

## 6. Non-Goals

Explicitly **not** required for the scoped end-state:

- **Full production infrastructure**: multi-region active-active, fleet-wide HA, autoscaling at scale, full SRE coverage for every component.
- **Large-scale distributed scheduling**: general-purpose global job grids; bounded async execution per runtime model only.
- **Exhaustive enterprise integrations**: every vendor API; a **small, representative** integration set suffices.
- **Fully polished end-user product UI**: consumer-grade UX and broad feature breadth in operator-console.
- **Perfect model performance**: SOTA benchmarks and model-agnostic tuning as a deliverable.
- **Autonomous self-modifying runtime behavior**: Mukti or models rewriting policy, plans, or tool registrations without a governed release path.

---

## 7. Differentiation

Compared to typical AI wrapper or framework-centric projects:

- **Execution semantics over prompt chaining**: Plans and steps are authoritative; models fill bounded roles.
- **Explicit control plane** instead of framework-driven flows: orchestrator, policy, tools, and knowledge are separate concerns with defined APIs.
- **Policy and governance as first-class concerns**: Stored decisions and approvals, not implied from chat.
- **Replayability and auditability**: Post-incident and review-friendly without reverse-engineering prompts.
- **Separation of agents, tools, and policy**: Propose vs evaluate vs execute are distinct.
- **Post-execution learning via Mukti**: Offline relative to live runs; advisory only (constitution §6.2–6.3).

This is an architectural stance, not a marketing claim.

---

## 8. Phase Outputs

Each phase lists **concrete artifacts**. “Stubbed” means interfaces or thin implementations that honor boundaries but are not production-complete for that concern.

### Phase 0 — Architecture Foundation

**Output:**

- **Constitution** and **runtime model** fixed as normative for implementation.
- **API design** (`/v1` execution-oriented surface, internal vs external split) agreed.
- **DB schema** direction in `infra/db/migrations/` aligned to trace and replay needs.
- **Service boundaries** documented (e.g. system overview); orchestrator scope explicit.
- **Shared contracts** in `packages/common-schemas` (or equivalent) for cross-service types.
- **End-state definition** (this document) for alignment and phase gates.

**May remain stubbed:** Executable services; all runtime behavior.

---

### Phase 1 — Execution Core

**Output:**

- **Working orchestrator**: drives create → plan → steps → validation gate → terminal states per runtime model and constitution §6.1.
- **State machine** for execution and step transitions enforced in code.
- **In-memory repository** for fast tests and local use.
- **DB-backed repository** persisting executions, contexts, plans, steps, step results against the operational schema.
- **Execution persistence** as the system of record for the graph above.
- **Replay foundation**: stored structure and inputs sufficient to support replay APIs when gateway/orchestrator expose them (exact vs investigative per api-design).
- **Tests** proving lifecycle correctness (valid/invalid transitions, validation-before-completion).

**May remain stubbed:** Real policy-engine, tool-runtime, knowledge-service, LLM calls; gateway HTTP may be absent if orchestrator is invoked in-process.

---

### Phase 2 — First Workflow

**Output:**

- **Incident triage** (or equivalently agreed first vertical) implemented on the common execution model.
- **Realistic workflow-specific** structured step results (not only generic placeholders).
- **Workflow-specific trace timeline** events and/or normalized rows inspectable.
- **Validation path** exercised **end-to-end** for that workflow’s success criteria.

**May remain stubbed:** Second workflow; full policy depth; large tool catalog; production gateway hardening.

---

### Phase 3 — Governance Layer

**Output:**

- **Policy-engine foundation**: synchronous evaluation API used by orchestrator; allow/deny/conditional with persisted **policy_evaluations** (or equivalent).
- **Action proposal lifecycle**: proposals created, status transitions recorded, linked to executions/steps.
- **Approval flow**: at least one path where human approval gates progression; **approvals** persisted.
- **Auditable policy decisions**: reasons and rule references stored; visible in trace projections.
- **Governed side-effect path**: tool calls for mutating tools occur only after policy (and approval when required)—no agent-direct mutation.

**May remain stubbed:** Complex rule packs, dynamic policy reload without deploy, multi-tenant policy UI.

---

### Phase 4 — Tool and Knowledge Layer

**Output:**

- **Tool-runtime** with a **small set of real tools** (e.g. read-only + one state-changing example) meeting contract fields (side-effect class, idempotency).
- **Knowledge-service foundation**: retrieval endpoint(s) orchestrator can call; tenant/workflow scoping documented.
- **Evidence-bearing step results** for at least one workflow step (citations/pointers in `evidence` per schema).
- **Retrieval and tool calls visible in trace** (normalized rows queryable).

**May remain stubbed:** Large corpora, embedding pipelines at scale, many tool adapters.

---

### Phase 5 — AI and Reasoning Layer

**Output:**

- **LLM-backed planner** *or* **bounded reasoning step** producing **structured** outputs validated against shared schemas (not unbounded prose as the only artifact).
- **Controlled use of AI inside execution**: model calls only inside step boundaries; orchestrator retains deterministic transitions.
- **No change to deterministic control plane**: state ownership and validation gates unchanged; constitution §2.3 and §8.4 preserved.

**May remain stubbed:** Fine-tuned models, elaborate prompt registries, automatic re-planning without human/policy triggers where not yet specified.

**Implementation note**

AI is introduced only through a bounded model-runtime service. Model outputs are structured, step-scoped, and do not influence execution state transitions. The orchestrator selects between model-runtime and deterministic fallback paths, and all model usage is traceable. This preserves a deterministic control plane while enabling AI-assisted reasoning.

---

### Phase 6 — Feedback and Mukti

**Output:**

- **Feedback-service integrated**: ingest path from gateway or orchestrator per api-design; durable feedback records.
- **Execution feedback persistence**: Mukti writes **execution_feedback** (or equivalent) linked to executions.
- **Failure classification** and **pattern detection** in structured output (not only narrative).
- **Advisory improvement suggestions**: explicit non-mutation of live runs (constitution §6.3).

**May remain stubbed:** ML-heavy clustering at scale, real-time Mukti triggers, operator-facing analytics warehouse.

---

### Phase 7 — Portfolio Hardening

**Output:**

- **High-visibility docs** filled (overview, key architecture pages, workflow walkthroughs—not empty TODO shells).
- **Diagrams** reflecting service boundaries and main flows.
- **Example traces** (redacted or synthetic) checked in or generated reproducibly.
- **Workflow walkthroughs** for at least two major workflows.
- **Polished README**: clone, migrate, run demo, run tests, link to constitution and end-state.
- **Clear demo path**: ordered steps an engineer can follow to observe a full path including policy and validation.

**May remain stubbed:** Full production runbooks, every ADR expanded, exhaustive diagram set.

---

### Phase 8 — Product Layer and Operational Surface

**Output:**

- **API Gateway**
  - REST endpoints for **executions**, **trace**, **approvals**, **replay**, and **metrics/evaluation** projections (aligned with [api-design.md](../architecture/api-design.md); add metrics/evaluation read paths as documented).
  - **Request validation** and **routing** to orchestrator and other allowed backends; authentication hooks as deployment attaches.

- **Operator Console (UI)**
  - **Execution explorer**: list, filter, search (within API capabilities).
  - **Execution detail**: timeline, steps, evidence, model paths (as exposed in trace), tools, policy.
  - **Approval interface** for gated executions.
  - **Mukti insights** view: per-execution and **cross-execution (v2)** insights as exposed by APIs.

- **Evaluation Engine**
  - Metrics **computed from execution data** (§2.8).
  - **Aggregation** by workflow, step type, tool, policy rule (as persisted).
  - **Anomaly detection signals** and degradation indicators per defined rules or statistical thresholds.

- **Mukti v2**
  - **Cross-execution insights** (§2.10): failure clustering, patterns, ranked improvement suggestions.
  - **Advisory** records only; **no** live execution or control-plane mutation.

- **Replay Capability**
  - **Exact** and **investigative** replay flows exposed per API (or supported CLI with same semantics).
  - **Difference inspection** between source and replay runs (metadata and trace-level comparison).

- **Second Workflow (cost vertical)**
  - **Cost attribution and analysis** implemented with **workflow-specific** tools and/or retrieval, **validation**, and a **governance path** (policy/approval where applicable)—not a generic two-step placeholder.

**May remain stubbed:**

- Full-scale UI polish and accessibility programs.
- Enterprise-grade auth systems beyond documented hooks and environment-scoped integration.
- Distributed metrics pipelines at fleet scale.
- Large-scale data warehouse or OLAP platform for analytics.

---

## 9. Evolution Path

After the scoped end-state:

- **Deeper policy models** and stricter conditional flows.
- **Richer tool integrations** under the same registration and audit pattern.
- **Stronger retrieval** (corpus size, ranking, evaluation).
- **More workflows** reusing the same execution and trace model.
- **Stronger evaluation and benchmarking** of step outputs, validators, and §2.8 platform metrics—including richer frameworks, held-out sets, and regression gates.
- **Operational hardening**: HA, scaling, SLOs, on-call playbooks—outside the current completion definition but enabled by the same boundaries.
- **UI expansion** for operators and analysts (dashboards, saved views, collaboration)—without collapsing service boundaries.
- **Deeper cross-workflow insights** (Mukti and evaluation-engine) as trace volume grows.
- **Scaling gateway and UI** for multi-tenant environments (quotas, isolation hardening, regional ingress)—beyond Phase 8 single-environment depth.

Extensions must not collapse orchestrator, policy, tools, or Mukti into a single implicit agent loop.

---

## Assumptions left open (intentional)

- **Minimum workflow pair for §5:** **Incident triage** and **cost attribution and analysis** are **required** full verticals; additional workflows in §3 remain as specified. Policy-aware behavior is demonstrated inside at least one of them or as a clearly linked scenario.
- **Gateway vs in-process orchestrator:** Phases **0–7** may progress with library or thin ingress as today; **Phase 8** requires a **real** **api-gateway** and **operator-console** for completion per §5. Early phases may still use CLI/tests where Phase 8 is not in scope.
- **Replay “exact” fidelity** to external systems may require recorded stubs; replay guarantees apply to **platform-stored** structure and inputs per runtime model.
