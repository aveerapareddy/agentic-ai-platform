# Documentation index

Compact map of repository documentation. Platform behavior is defined by [constitution](overview/project-constitution.md) and [end state](overview/project-end-state.md)—not by this index alone.

## Overview

| Doc | Topic |
|-----|--------|
| [project-constitution.md](overview/project-constitution.md) | Non-negotiable engineering rules |
| [project-end-state.md](overview/project-end-state.md) | Target capabilities and phases |
| [problem-statement.md](overview/problem-statement.md) | Problem framing |
| [scope-and-non-goals.md](overview/scope-and-non-goals.md) | In / out of scope |

## Architecture

| Doc | Topic |
|-----|--------|
| [system-overview.md](architecture/system-overview.md) | Services and trust boundaries |
| [runtime-model.md](architecture/runtime-model.md) | Execution, plan, step semantics |
| [api-design.md](architecture/api-design.md) | HTTP `/v1` contracts |
| [security-and-guardrails.md](architecture/security-and-guardrails.md) | RBAC, policy surface |
| [storage-design.md](architecture/storage-design.md) | Persistence layout |
| [observability-and-reliability.md](architecture/observability-and-reliability.md) | Trace and failure classification |

ADRs: [decisions/](decisions/).

## Workflows

| Doc | Topic |
|-----|--------|
| [incident-triage-walkthrough.md](workflows/incident-triage-walkthrough.md) | Demo path: incident workflow |
| [cost-attribution-walkthrough.md](workflows/cost-attribution-walkthrough.md) | Demo path: cost workflow |
| [replay-investigation-walkthrough.md](workflows/replay-investigation-walkthrough.md) | Replay and diff |
| [incident-triage.md](workflows/incident-triage.md) · [cost-attribution.md](workflows/cost-attribution.md) | Workflow definitions |

## Runbooks

| Doc | Topic |
|-----|--------|
| [local-development.md](runbooks/local-development.md) | Docker stack, migrate, seed, troubleshoot |
| [incident-workflow-demo.md](runbooks/incident-workflow-demo.md) | Orchestrator-only demo |
| [replaying-executions.md](runbooks/replaying-executions.md) | Replay modes |

## Diagrams & assets

| Path | Topic |
|------|--------|
| [diagrams/README.md](diagrams/README.md) | SVG + draw.io architecture diagrams |
| [assets/screenshots/](assets/screenshots/) | Operator-console demo captures |
| [examples/](examples/) | Sample trace and replay-diff JSON |

## Product / UI

| Doc | Topic |
|-----|--------|
| [ui-system.md](design/ui-system.md) | Operator-console design system |
| [../services/operator-console/README.md](../services/operator-console/README.md) | Console routes and API usage |
