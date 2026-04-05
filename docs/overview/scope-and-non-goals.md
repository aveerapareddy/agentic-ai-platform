# Scope and non-goals

One-line purpose: bound what the platform will and will not attempt.

## In scope (repository today)

- **Execution control plane** in `services/orchestrator`: planning, step scheduling, state machine, validation phase, integration hooks for policy, tools, knowledge, model-runtime.
- **Governance**: `services/policy-engine`; persisted proposals, evaluations, approvals; `incident_triage` escalation path.
- **Tools and retrieval**: `services/tool-runtime`, `services/knowledge-service` with deterministic local implementations.
- **Bounded AI**: `services/model-runtime` with structured outputs and orchestrator-side fallback.
- **Feedback loop**: `services/feedback-service`, `services/mukti-agent` (rule-based), post-execution only.
- **Contracts**: `packages/common-schemas`.
- **Operational DDL**: `infra/db/migrations/` (executions, steps, results, tool_calls, policy, approvals, execution_feedback, operator_feedback per migrations).

## Explicit non-goals

Aligned with **project-end-state.md §6** and **constitution**:

- **Full production fleet**: multi-region active-active, exhaustive SRE runbooks, autoscaling matrices for every service—out of scope for this repo’s current phase.
- **Framework-as-orchestrator**: LangChain / LangGraph (or similar) as the core execution engine—excluded by constitution §8.3.
- **Mukti mutating live runs** or **calling orchestrator control APIs**—excluded by constitution §6.2–6.3 and architecture.
- **Autonomous self-modifying runtime**: policy, tools, or prompts rewritten from Mukti output without governed release—excluded.
- **Heavy analytics warehouse** and **ML-first Mukti**—stubbed; current Mukti is deterministic rules.
- **api-gateway and operator-console implementations**—directories exist as placeholders; no runnable HTTP/UI product in tree.
- **Real enterprise API integrations** in tool-runtime for this portfolio snapshot—tools are local/deterministic stand-ins.

## Boundaries with adjacent systems

- **Identity and rate limiting**: intended at **api-gateway** (per `api-design.md`); not implemented here.
- **Secrets**: expected from environment/secret store at deploy time; no vault product embedded.
- **Message buses for Mukti**: optional in architecture; current triggering is **direct invocation** in tests and helpers—no queue requirement met in code.

## Versioning and change policy

Shared contracts evolve per **constitution §7.3**: breaking changes require explicit justification. Database changes additive where possible (`002_operator_feedback.sql` pattern). Runtime semantics remain governed by **constitution** and **runtime-model.md**; implementation must not silently diverge.
