# Target users

One-line purpose: identify primary consumers of the platform and their responsibilities.

## Platform engineering

Owns service deployment, database migrations, connectivity between orchestrator, policy-engine, tool-runtime, knowledge-service, model-runtime, feedback-service, and mukti-agent. Integrates identity and network policy at the boundary (when **api-gateway** exists). Ensures observability and backup cover execution and feedback stores.

## SRE and incident response

Consumes **executions**, **traces**, and **step results** to understand automated triage paths. Uses **approvals** where policy requires human gates. Relies on explicit failure and governance events in the trace—not on reconstructing behavior from model transcripts alone.

## FinOps and cost ownership

**Intended** consumers for a future **cost attribution** vertical: cross-system reasoning with retrieval-backed evidence and auditable tool access. **Today**, the repository only provides a **generic** two-step planner path for non–`incident_triage` workflows; FinOps-specific capabilities are not implemented.

## Security and compliance

Reviews **policy evaluations**, **approvals**, **tool_calls**, and **execution_context** (tenant, environment, policy scope) for evidence of control. Expects **no direct client access** to internal services (per `system-overview.md`); external access is intended to route through a gateway with authn/authz hooks.

## Application owners

Define workflow inputs, validation expectations, and which tools and knowledge scopes are appropriate for their domain. They do **not** bypass orchestration to call tool-runtime or policy-engine directly from user-facing clients.

## Why this is a platform, not a single product

Multiple workflows (incident, cost, policy-heavy actions) share the **same execution model**, **same trace shape**, and **same governance surfaces**. New verticals add planners, tools, and validators—not a separate runtime per use case.

## Out of scope personas

End customers of a SaaS chat product; users expecting autonomous agents that mutate production without policy and approval paths. This repository does not target them.
