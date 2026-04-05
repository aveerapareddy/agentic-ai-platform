# High-level architecture

One-line purpose: conceptual layers and how execution, policy, tools, retrieval, AI, and Mukti compose—**complementary** to [system-overview.md](system-overview.md), which remains the authoritative service-by-service matrix.

## Platform layers

1. **Ingress (designed, not implemented in tree)**  
   **api-gateway**: external HTTP, authn/authz, routing to orchestrator and feedback paths per [api-design.md](api-design.md).

2. **Control runtime**  
   **orchestrator**: owns execution lifecycle, when to call policy / tools / knowledge / model-runtime, persistence of the execution graph and trace timeline projection. Does **not** embed policy rules, tool code, retrieval indexes, or Mukti.

3. **Governance**  
   **policy-engine**: synchronous allow/deny/conditional; returns structured evaluations for proposals (and is isolated from tool execution).

4. **Execution surface**  
   **tool-runtime**: registered tools only; returns `ToolCall` records for persistence.

5. **Retrieval**  
   **knowledge-service**: scoped retrieval; returns structured chunks for step evidence—not execution state.

6. **Bounded inference**  
   **model-runtime**: structured reasoning outputs for specific step types (`analyze_incident`, `validate_incident` today); orchestrator chooses model path vs `StepExecutor` fallback.

7. **Post-execution improvement**  
   **feedback-service**: operator feedback rows; storage for Mukti `execution_feedback`.  
   **mukti-agent**: consumes frozen `MuktiAnalysisInput`; emits advisory `ExecutionFeedback`; **no** orchestrator callbacks.

## Major interactions (happy-path mental model)

External client → (gateway) → **orchestrator** → **policy-engine** / **tool-runtime** / **knowledge-service** / **model-runtime** as steps require → PostgreSQL (or in-memory repo) for executions, steps, results, tool_calls, governance, feedback tables.

## How the pieces fit on the incident triage path

- **Planning**: orchestrator + **Planner** (deterministic JSON plan spec).
- **Reasoning**: **model-runtime** or fallback executor inside step boundaries.
- **Evidence**: **tool-runtime** + **knowledge-service** orchestrated only for `gather_evidence`.
- **Validation**: explicit step + recorded outcome before terminal success.
- **Governance**: policy + optional approval before completing after validation.
- **After termination**: optional **feedback-service** + **mukti-agent** on snapshots.

## Control plane vs data plane

**Control plane:** execution status transitions, policy decisions, approval records, scheduling—owned by orchestrator + policy-engine + persistence adapters.

**Data plane (tool/knowledge side effects):** today **simulated** (read-only local tools, in-memory corpus). Intended production shape: tool-runtime credentials and knowledge indexes **outside** the execution row store.

## Synchronous vs asynchronous

Hot path (step execution, policy eval, tool call, retrieval, model call) is **synchronous** in process today. **Mukti** is **off** the completion path: analysis does not block marking an execution complete. Async fan-out from feedback-service to Mukti is **architecturally allowed** but **not implemented** as a queue.

## Failure domains

Described in [system-overview.md](system-overview.md) §6 and [observability-and-reliability.md](observability-and-reliability.md): tool-runtime and knowledge-service failures affect only dependent steps; policy-engine unavailability blocks gated transitions; Mukti backlog does not affect running executions.
