# Security and guardrails

One-line purpose: access, policy, and audit expectations aligned with implemented behavior and documented boundaries.

## Threat model (engineering view)

- **Untrusted callers** must not reach **orchestrator**, **policy-engine**, **tool-runtime**, **knowledge-service**, or **model-runtime** directly; **api-gateway** is the intended edge ([system-overview.md](system-overview.md)).
- **Tool credentials** are service-scoped; end users do not hold them.
- **Mukti** must not obtain live execution control messages or orchestrator admin APIs.

## Identity and access (Session E — local/dev foundation)

Production shape: gateway validates identity and maps to **execution_context** fields (`tenant_id`, `principal_id`, `permissions_scope`, `policy_scope`, `environment`). Orchestrator persists context and propagates IDs to tool calls and policy evaluation inputs.

### Auth header model (development)

| Header | Purpose |
|--------|---------|
| `X-Principal-Id` | Authenticated user or service principal |
| `X-Tenant-Id` | Trusted tenant scope |
| `X-Roles` | Comma-separated roles: `viewer`, `operator`, `approver`, `admin` |

When headers are absent, `GATEWAY_ALLOW_DEV_PRINCIPAL_FALLBACK=true` (default) supplies `GATEWAY_DEV_PRINCIPAL_ID`, `GATEWAY_DEV_TENANT_ID`, and `GATEWAY_DEV_ROLES`. Set fallback to **false** in shared environments.

**Not implemented:** OIDC/JWT validation, mTLS client certs, or centralized IAM integration. These belong behind a future `AuthProvider` interface at the gateway edge.

### RBAC (gateway only)

| Capability | Roles |
|------------|--------|
| List/read executions, trace, replay diff | `viewer`, `operator`, `approver`, `admin` |
| Create executions, feedback, replay, cancel | `operator`, `admin` |
| Submit approvals | `approver`, `admin` |
| List policy rules, simulate policy | `admin` |

Denied requests return structured **403** with `error.code: FORBIDDEN`. Missing identity (fallback disabled) returns **401**.

### Tenant propagation

- Gateway **merges** trusted `tenant_id` and `principal_id` into execution `context` on create.
- Client-supplied `context.tenant_id` that **conflicts** with the authenticated tenant is rejected (**400**).
- Execution reads verify the stored execution context tenant matches the caller.

**Policy evaluation** remains in **policy-engine**; the gateway does not implement allow/deny business rules except RBAC.

## Policy gates

- **policy-engine** evaluates explicit requests; agents do not self-approve.
- **Conditional** outcomes can force **awaiting_approval**; **deny** records a terminal governance outcome without executing governed side effects in the incident path implemented today.
- **Policy simulation** (`POST /v1/policies/simulate`) calls the same evaluator as runtime proposals; it does not mutate rule packs.

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

## Limitations

- No OAuth/OIDC provider wiring in this repository snapshot.
- RBAC is coarse role-based, not resource-level ABAC.
- Operator-console sends dev auth headers via HTTP interceptor for local use only; production must attach real identity at the gateway edge.
