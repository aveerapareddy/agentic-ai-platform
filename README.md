# Agentic AI Platform

Internal platform for governed, observable multi-agent workflows over enterprise systems. It coordinates planning, execution, validation, policy, retrieval, and controlled improvement with explicit execution semantics and full traceability.

## Why this platform exists

Enterprise automation over heterogeneous systems requires bounded agent roles, deterministic policy for high-risk actions, auditable tool access, and reproducible evaluation. Ad hoc LLM integrations do not meet operational, security, or compliance expectations for incident response, cost governance, or regulated execution paths.

## Core workflows

- Incident triage and root cause analysis
- Cross-system cost attribution and optimization
- Policy-aware action execution
- Mukti Agent: post-execution analysis and controlled improvement (observability layer; no uncontrolled self-modification)

## Architecture themes

Explicit execution over implicit prompting; separation of planning, execution, validation, policy, retrieval, and action; bounded agents only; mandatory observability and failure handling; traceable retrieval; learning via feedback and controlled improvement; registered, permissioned, auditable tools; validation for non-trivial outputs; policy layer isolated from agent logic.

## Repository map

| Path | Purpose |
|------|---------|
| `docs/` | Product definition, architecture, workflows, ADRs, diagrams, runbooks |
| `services/` | Deployable services (API gateway, orchestrator, policy, tools, knowledge, feedback, Mukti Agent, operator console) |
| `packages/` | Shared schemas, contracts, observability utilities, client SDK |
| `infra/` | Containers, Terraform, Kubernetes, Cloud Run, monitoring, database migrations |
| `evals/` | Datasets, traces, regression, scoring, reports |
| `scripts/` | Bootstrap, local development, seed data, replay, CI helpers |
| `examples/` | Demonstrations supporting the platform (not the product definition) |
| `tests/` | Integration, contract, and end-to-end tests |

## Current status

Documentation skeleton and repository layout are in place. Service and package implementations are not yet started beyond structural placeholders.

## Documentation

- [Overview](docs/overview/)
- [Architecture](docs/architecture/)
- [Workflows](docs/workflows/)
- [Architecture decision records](docs/decisions/)
- [Runbooks](docs/runbooks/)
