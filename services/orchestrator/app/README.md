# Orchestrator (Phase 1)

In-memory execution engine: planning, step simulation, lifecycle transitions aligned with `common-schemas` and the runtime model.

## Run locally

From `services/orchestrator` (with `common-schemas` installed or on `PYTHONPATH`):

```bash
pip install -e ../../packages/common-schemas
export PYTHONPATH=../../packages/common-schemas/src:.
python -m pytest app/tests -v
python -m app.main
```

Persistence, policy, tools, and knowledge calls are stubbed.
