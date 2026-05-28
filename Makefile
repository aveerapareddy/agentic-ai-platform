# Local development targets (Session G). Run from repository root.

PYTHON ?= python3
REPO_ROOT := $(shell pwd)
export PYTHONPATH := $(REPO_ROOT)/packages/common-schemas/src:$(REPO_ROOT)/packages/observability/src:$(REPO_ROOT)/services/orchestrator:$(REPO_ROOT)/services/policy-engine:$(REPO_ROOT)/services/tool-runtime:$(REPO_ROOT)/services/knowledge-service:$(REPO_ROOT)/services/model-runtime:$(REPO_ROOT)/services/feedback-service:$(REPO_ROOT)/services/mukti-agent:$(REPO_ROOT)/services/evaluation-engine:$(REPO_ROOT)/services/api-gateway

DATABASE_URL ?= postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agentic_dev
export DATABASE_URL

.PHONY: help setup install-py install-js migrate migrate-dry-run seed test test-gateway test-orchestrator \
	run-gateway run-console docker-up docker-down docker-seed health-smoke smoke-stack capture-screenshots

help:
	@echo "Targets:"
	@echo "  setup          - install Python + Node dependencies"
	@echo "  migrate        - apply SQL migrations (requires Postgres)"
	@echo "  seed           - demo data via api-gateway (GATEWAY_URL)"
	@echo "  run-gateway    - uvicorn api-gateway on :8080 (in-memory unless GATEWAY_USE_POSTGRES=true)"
	@echo "  run-console    - ng serve operator-console on :4200"
	@echo "  docker-up      - postgres + api-gateway + operator-console"
	@echo "  docker-down    - stop compose stack"
	@echo "  docker-seed    - run seed profile after stack is up"
	@echo "  test           - gateway + orchestrator unit tests"
	@echo "  health-smoke   - curl gateway /health/runtime"
	@echo "  smoke-stack    - gateway health, /v1/metrics, executions list (optional console)"
	@echo "  capture-screenshots - PNGs from docs/assets/screenshot-fixtures (playwright)"

setup: install-py install-js

install-py:
	$(PYTHON) -m pip install -e packages/common-schemas -e packages/observability
	$(PYTHON) -m pip install -e services/orchestrator -e services/api-gateway
	$(PYTHON) -m pip install sqlalchemy 'psycopg[binary]' httpx

install-js:
	cd services/operator-console && npm install

migrate:
	$(PYTHON) scripts/apply_migrations.py

migrate-dry-run:
	$(PYTHON) scripts/apply_migrations.py --dry-run

seed:
	GATEWAY_URL=$${GATEWAY_URL:-http://127.0.0.1:8080} $(PYTHON) scripts/seed_demo_data.py

health-smoke:
	curl -sf $${GATEWAY_URL:-http://127.0.0.1:8080}/health/runtime | $(PYTHON) -m json.tool

smoke-stack:
	GATEWAY_URL=$${GATEWAY_URL:-http://127.0.0.1:8080} $(PYTHON) scripts/smoke_local_stack.py

capture-screenshots:
	$(PYTHON) scripts/capture_demo_screenshots.py

test: test-gateway test-orchestrator test-scripts

test-scripts:
	$(PYTHON) -m pytest scripts/tests -q

test-gateway:
	cd services/api-gateway && $(PYTHON) -m pytest gateway/tests -q

test-orchestrator:
	cd services/orchestrator && $(PYTHON) -m pytest app/tests -q

run-gateway:
	cd services/api-gateway && \
		MODEL_PROVIDER=$${MODEL_PROVIDER:-fake} \
		GATEWAY_ALLOW_DEV_PRINCIPAL_FALLBACK=true \
		uvicorn gateway.main:app --host 127.0.0.1 --port 8080 --reload

run-console:
	cd services/operator-console && npm start

docker-up:
	docker compose up -d postgres
	$(MAKE) migrate
	docker compose up -d --build api-gateway operator-console

docker-down:
	docker compose down

docker-seed:
	docker compose --profile seed run --rm seed
