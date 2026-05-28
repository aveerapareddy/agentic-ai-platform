# Local development

One-line purpose: run the platform as a credible internal demo—Docker stack, migrations, seed data, api-gateway, and operator-console.

## Prerequisites

- **Docker** and **Docker Compose** (for full stack), or **Python 3.11+** and **Node 20+** (for host-run gateway/console).
- No real LLM API keys required when `MODEL_PROVIDER=fake` (default).

## Quick start (Docker — recommended)

```bash
cp .env.example .env
make docker-up
make docker-seed    # optional: incident + cost executions, replay, feedback
```

| Service | URL |
|---------|-----|
| Operator console | http://localhost:4200 |
| API gateway | http://localhost:8080 |
| Prometheus ops metrics | http://localhost:8080/metrics |
| Runtime health | http://localhost:8080/health/runtime |

Open the console → **Executions** → select a seeded run → inspect trace, metrics, stream (**Live** badge), policies, insights.

## Architecture (local stack)

| Container | Role |
|-----------|------|
| **postgres** | Operational DDL from `infra/db/migrations/` |
| **api-gateway** | HTTP ingress; **orchestrator + policy + tools + knowledge + model-runtime + feedback + Mukti + evaluation** run **in-process** in this image (not separate microservice containers). |
| **operator-console** | nginx static UI; proxies `/v1`, `/metrics`, `/health` to api-gateway |

This preserves service boundaries in code while keeping local ops simple—**not** a monolith rewrite.

## Environment

Copy `.env.example` → `.env`. Important variables:

- `DATABASE_URL` — PostgreSQL for persisted mode.
- `GATEWAY_USE_POSTGRES` — `true` in compose; `false` for fast in-memory gateway on host.
- `MODEL_PROVIDER=fake` — deterministic model path, no external API.
- `GATEWAY_*` auth fallback and dev tenant/principal for header-less local use.
- `GATEWAY_USE_EXECUTION_WORKER_QUEUE` — background worker for executions.

**Never commit real API keys or production passwords.**

## Migrations

With Postgres running (compose or local):

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agentic_dev
make migrate
# or: python scripts/apply_migrations.py
# dry-run: make migrate-dry-run
```

Applies `001_initial_schema.sql` then `002_operator_feedback.sql` in order.

## Seed / demo data

Requires a healthy gateway:

```bash
make run-gateway   # or docker compose up api-gateway
make seed
```

`scripts/seed_demo_data.py` creates (via real APIs):

- `incident_triage` execution (runs to completion)
- `cost_attribution` execution
- optional **replay** child for the incident
- **operator feedback** samples
- **Mukti insights** read (`GET /v1/insights/mukti`)

Uses idempotency keys (`demo-seed-*-v1`); reset DB or change keys to re-seed.

## Host-run (without Docker UI build)

```bash
make setup
docker compose up -d postgres
make migrate

# Terminal 1
make run-gateway

# Terminal 2
make run-console

# Terminal 3 (optional)
make seed
```

Gateway on **:8080**; Angular dev server on **:4200** with proxy to gateway (`proxy.conf.json`).

## Makefile targets

| Target | Description |
|--------|-------------|
| `make setup` | Editable Python packages + console `npm install` |
| `make migrate` | Apply SQL migrations |
| `make seed` | Demo data through gateway |
| `make run-gateway` | uvicorn api-gateway |
| `make run-console` | `ng serve` |
| `make docker-up` | postgres + migrate + gateway + console |
| `make docker-down` | Stop stack |
| `make docker-seed` | Compose seed profile |
| `make test` | Gateway + orchestrator tests |
| `make health-smoke` | `GET /health/runtime` |
| `make smoke-stack` | Health + authenticated `/v1/metrics` + executions list (+ optional console) |

## Orchestrator-only demo (no HTTP)

Still supported for engine debugging:

```bash
cd services/orchestrator
PYTHONPATH=".:../../packages/common-schemas/src:../policy-engine:../tool-runtime:../knowledge-service:../model-runtime:../feedback-service:../mukti-agent" \
  python -m app.main
```

See [incident-workflow-demo.md](incident-workflow-demo.md).

## Health checks

- **Postgres:** compose `pg_isready` healthcheck.
- **api-gateway:** `GET /health/runtime` (model provider label); compose healthcheck uses this. Operational `GET /metrics` is unauthenticated (Prometheus counters including `policy_*`).
- **operator-console:** nginx serves `/`; API health proxied at `/health/runtime`.
- **SSE stream:** `GET /v1/executions/{id}/stream` (requires auth headers or dev fallback).
- **Smoke:** after `make docker-up`, run `make smoke-stack` (set `SMOKE_SKIP_CONSOLE=1` if console is not running).

## Common failures

| Symptom | Fix |
|---------|-----|
| Import errors on host | `make setup` or set `PYTHONPATH` per Makefile |
| Gateway 401 | Set `GATEWAY_ALLOW_DEV_PRINCIPAL_FALLBACK=true` or send `X-Principal-Id` / `X-Tenant-Id` / `X-Roles` |
| Migrate connection refused | Start postgres; check `DATABASE_URL` host (`127.0.0.1` vs `postgres`) |
| Seed timeout | Ensure gateway worker is running (`GATEWAY_USE_EXECUTION_WORKER_QUEUE=true`); increase wait in script |
| Console API errors | Confirm gateway on :8080; Docker console uses nginx proxy to `api-gateway` |
| Policy deny / awaiting approval | Use `policy_scope: default` and `environment: dev` in seed (defaults) |

## Cleaning state

- **Compose:** `make docker-down` (add `-v` to drop `pgdata` volume).
- **In-memory gateway:** restart process.

## Limitations

- Not production HA, Kubernetes, or cloud IaC.
- Single gateway container bundles runtime services for convenience.
- Mukti `execution_feedback` rows are not seeded via HTTP (insights use executions + operator feedback); full Mukti persistence path is available in orchestrator tests.
