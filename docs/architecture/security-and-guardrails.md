# Security and guardrails

One-line purpose: access, policy, and audit expectations aligned with implemented behavior and documented boundaries.

## Threat model (engineering view)

- **Untrusted callers** must not reach **orchestrator**, **policy-engine**, **tool-runtime**, **knowledge-service**, or **model-runtime** directly; **api-gateway** is the intended edge ([system-overview.md](system-overview.md)).
- **Tool credentials** are service-scoped; end users do not hold them.
- **Mukti** must not obtain live execution control messages or orchestrator admin APIs.

**Current repo gap:** **api-gateway** is not implemented; in-process tests and `app.main` bypass external auth—acceptable for development only.

## Identity and access

Production shape: gateway validates identity and maps to **execution_context** fields (`tenant_id`, `principal_id`, `permissions_scope`, `policy_scope`, `environment`). Orchestrator persists context and propagates IDs to tool calls and policy evaluation inputs. **Today**, tests construct context explicitly without IAM integration.

## Policy gates

- **policy-engine** evaluates explicit requests; agents do not self-approve.
- **Conditional** outcomes can force **awaiting_approval**; **deny** records a terminal governance outcome without executing governed side effects in the incident path implemented today.

## Approval flow

Approvals are **persisted** with links to executions and optionally policy evaluations or proposals. They are **auditable** and required for certain conditional branches before completion.

## Tool boundary controls

- Only **registered** tool names run through **tool-runtime**; orchestrator does not embed tool implementations.
- Contracts include **side_effect_class** and **idempotency** (see `common_schemas.tooling`). Current tools are **read_only** / **idempotent** stand-ins—no mutating production tools wired.

## No direct side effects from “workflows” alone

State-changing effects are **not** implemented in the portfolio snapshot; escalation and similar actions are recorded through governance artifacts, not executed against external ticket systems in code. Constitution §3.2 remains the design rule: mutations go through tool-runtime + policy (+ approval when required).

## Secrets management

Services are expected to load DB URLs and future API keys from environment or a secret store at deploy time. No secret manager SDK is bundled.

## Audit and non-repudiation

**Trace timeline** on executions plus normalized rows (steps, tool_calls, policy_evaluations, approvals, feedback) support “what happened” narratives. **Operator feedback** and **execution_feedback** are separate tables to avoid conflating human labels with Mukti output.

## Data protection

Classification, encryption at rest, and field-level redaction are **deployment concerns**; schemas use JSONB for flexibility but do not embed encryption logic.
