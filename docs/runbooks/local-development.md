# Local development

One-line purpose: environment setup, running the **orchestrator** demo, tests, and optional PostgreSQL for persistence experiments.

## Prerequisites

- **Python 3.11+**
- Dependencies for `packages/common-schemas` and service packages used by the orchestrator (install via each `pyproject.toml` or a workspace tool of your choice).

## Environment configuration

- No global `.env` is required for the in-memory demo.
- For PostgreSQL integration tests: set **`ORCHESTRATOR_TEST_DATABASE_URL`** to a reachable database (see `app/tests/test_postgres_repository_integration.py`).

## PYTHONPATH convention

The orchestrator imports sibling services and common-schemas. From `services/orchestrator`:

```text
PYTHONPATH=".:../../packages/common-schemas/src:../policy-engine:../tool-runtime:../knowledge-service:../model-runtime:../feedback-service:../mukti-agent"
```

Use the same prefix for `python -m pytest`.

## Running the orchestrator (demo)

```bash
cd services/orchestrator
PYTHONPATH=".:../../packages/common-schemas/src:../policy-engine:../tool-runtime:../knowledge-service:../model-runtime:../feedback-service:../mukti-agent" \
  python -m app.main
```

This runs **`incident_triage`** end-to-end in memory (see [incident-workflow-demo.md](incident-workflow-demo.md)).

There is **no** long-lived HTTP server for orchestrator in this layout; **api-gateway** is a placeholder directory.

## Running tests

```bash
cd services/orchestrator
PYTHONPATH=".:../../packages/common-schemas/src:../policy-engine:../tool-runtime:../knowledge-service:../model-runtime:../feedback-service:../mukti-agent" \
  python -m pytest app/tests -q
```

Other packages (`policy-engine`, `tool-runtime`, etc.) may have their own tests under `tests/`; run `pytest` from each service root if you change that code.

## Optional database setup

1. Start PostgreSQL locally.
2. Apply DDL: `infra/db/migrations/001_initial_schema.sql`, then `002_operator_feedback.sql` (order matters).
3. Point `ORCHESTRATOR_TEST_DATABASE_URL` at that database and run the postgres repository integration test module.

Feedback and Mukti rows in migrations align with **feedback-service** persistence when wired to a shared DB; the default `FeedbackService()` in tests uses **`InMemoryFeedbackRepository`**, separate from execution repository unless you configure otherwise.

## Common failures

- **Import errors**: PYTHONPATH missing a sibling service or `common-schemas/src`.
- **Policy unexpected outcome**: check `environment` and `policy_scope` (`phase3_deny`, `phase3_conditional`, `prod` trigger deny/conditional per evaluator).
- **Model path**: if `ModelRuntimeService` is disabled or `None`, incident analyze/validate use **StepExecutor** only; timeline shows `deterministic_fallback` when model throws.

## Cleaning state

- In-memory: exit the process.
- PostgreSQL: drop or truncate tables per your environment policy (no automated teardown in repo).
