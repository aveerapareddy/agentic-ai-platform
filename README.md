# Agentic AI Platform

A governed execution control plane for multi-step workflows that use models, registered tools, and retrieval under explicit lifecycle, policy, and trace semantics. The repository targets an **internal platform** shape: durable executions, auditable decisions, and service boundaries suitable for extension—not a conversational product or framework-driven demo.

## What the system is

- **Orchestrated executions**: `execution` → `plan` → `steps` with deterministic state transitions (`created` → `planning` → `executing` → `validating` → terminal states, plus `awaiting_approval` where policy requires it).
- **Separated concerns**: policy evaluation (`policy-engine`), tool invocation (`tool-runtime`), retrieval (`knowledge-service`), structured model calls (`model-runtime`), operator and Mukti persistence (`feedback-service`), post-execution analysis (`mukti-agent`), coordinated by **`orchestrator`** only.
- **Contracts first**: cross-service types live in `packages/common-schemas`; PostgreSQL schema in `infra/db/migrations/` aligns with persistence adapters in the orchestrator and feedback layers.

## Why it exists

Operational work over many systems needs **bounded automation**: side effects and high-risk actions must be **policy-gated**, **tool-audited**, and **replayable**. Model output alone is insufficient as a control mechanism. This codebase encodes that split: the control plane stays deterministic; models and tools operate inside step boundaries with structured inputs and outputs.

## Core workflows (intent vs current depth)

| Workflow | Role in the platform | Implementation today |
|----------|----------------------|------------------------|
| **Incident triage** | Structured analyze → evidence → validate → governance on escalation | **Full vertical** in orchestrator: planner, model-runtime for analyze/validate, tool-runtime + knowledge-service for `gather_evidence`, policy + approvals for `escalate_incident`, trace events. |
| **Cost attribution** | Cross-system cost reasoning with retrieval and tools | **Scaffold**: same default two-step plan as other non–`incident_triage` workflows (`reasoning` → `validation`); no cost-specific tools or planners yet. |
| **Policy-aware execution** | Deny / conditional / allow with proposals and approvals | **Implemented** on `incident_triage` completion path (policy-engine + persisted proposals, evaluations, approvals). |
| **Feedback / Mukti** | Post-execution labels and advisory execution feedback | **Implemented**: `feedback-service` (operator + Mukti rows), `mukti-agent` deterministic analyzer, `build_mukti_analysis_input` for frozen snapshots; **no** mutation of live executions. |

## Architecture themes

Deterministic scheduling and validation-before-success; policy and tools **not** embedded in the orchestrator’s rule set; **no** LangChain/LangGraph as the execution engine; trace materialized as timeline JSON on executions plus normalized rows (steps, results, tool calls, policy, approvals, feedback tables per migrations).

## Repository map

| Path | Purpose |
|------|---------|
| `docs/` | Constitution, end-state, architecture, workflows, ADRs, runbooks |
| `packages/common-schemas/` | Shared Pydantic contracts |
| `services/orchestrator/` | Execution engine, planner, persistence adapters, in-process demo entrypoint |
| `services/policy-engine/` | Deterministic policy evaluation |
| `services/tool-runtime/` | Registered tools (`incident_metadata_tool`, `signal_lookup_tool`) |
| `services/knowledge-service/` | Local corpus retrieval for evidence |
| `services/model-runtime/` | Structured reasoning client; default fake provider |
| `services/feedback-service/` | Operator feedback + `execution_feedback` persistence |
| `services/mukti-agent/` | Post-execution advisory analysis |
| `services/api-gateway/`, `services/operator-console/` | **Placeholders** (no runtime implementation in tree) |
| `infra/db/migrations/` | PostgreSQL DDL (`001_initial_schema.sql`, `002_operator_feedback.sql`) |
| `evals/`, `examples/`, `scripts/` | Present for future use; not required for core tests |

## Current implementation status

Phases **1–6** of `docs/overview/project-end-state.md` are represented in code to the depth described there: execution core, incident triage as the primary workflow, governance, tools/knowledge on evidence steps, bounded model-runtime, feedback + rule-based Mukti. **api-gateway** and **operator-console** are not implemented as services. **Cost attribution** is not a dedicated vertical beyond the generic planner path.

## How to run the main demo path

From the repository root, with Python 3.11+ and dependencies installed for `common-schemas` and orchestrator path deps (e.g. editable installs or `PYTHONPATH`):

```bash
cd services/orchestrator
PYTHONPATH=".:../../packages/common-schemas/src:../policy-engine:../tool-runtime:../knowledge-service:../model-runtime:../feedback-service:../mukti-agent" \
  python -m app.main
```

This creates an `incident_triage` execution in memory, runs it to completion (including policy allow path by default), and prints step summaries. It does **not** start HTTP servers or Mukti automatically; post-execution Mukti is invoked explicitly in tests via `build_mukti_analysis_input` + `MuktiService` + `FeedbackService` (see `app/tests/test_phase6_feedback_mukti.py`).

### Tests (representative)

```bash
cd services/orchestrator
PYTHONPATH=".:../../packages/common-schemas/src:../policy-engine:../tool-runtime:../knowledge-service:../model-runtime:../feedback-service:../mukti-agent" \
  python -m pytest app/tests -q
```

PostgreSQL-backed tests are optional (`ORCHESTRATOR_TEST_DATABASE_URL`); see `app/tests/test_postgres_repository_integration.py`.

## Documentation

- [Constitution](docs/overview/project-constitution.md) — non-negotiable principles  
- [End state & phases](docs/overview/project-end-state.md) — scope and maturity targets  
- [System overview](docs/architecture/system-overview.md) — services and trust boundaries  
- [Runtime model](docs/architecture/runtime-model.md) — execution semantics  
- [API design](docs/architecture/api-design.md) — intended HTTP surface (not all wired)
