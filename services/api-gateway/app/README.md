# Note on `app/` vs `gateway/`

Phase 8 HTTP code is implemented as the **`gateway`** Python package (`services/api-gateway/gateway/`) to avoid a name clash with the orchestrator’s **`app`** package (`services/orchestrator/app/`).

See [../README.md](../README.md) for purpose, endpoints, and how to run.
