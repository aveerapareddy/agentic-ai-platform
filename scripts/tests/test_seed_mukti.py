"""Mukti persistence helpers in seed_demo_data (service-contract path)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
# orchestrator last so insert(0) leaves it first on sys.path (before other services' app/ stubs).
_EXTRA_PATHS = [
    ROOT / "packages" / "common-schemas" / "src",
    ROOT / "packages" / "observability" / "src",
    ROOT / "services" / "policy-engine",
    ROOT / "services" / "tool-runtime",
    ROOT / "services" / "knowledge-service",
    ROOT / "services" / "model-runtime",
    ROOT / "services" / "feedback-service",
    ROOT / "services" / "mukti-agent",
    ROOT / "services" / "orchestrator",
]
for p in _EXTRA_PATHS:
    s = str(p.resolve())
    if s not in sys.path:
        sys.path.insert(0, s)


def _load_seed():
    path = ROOT / "scripts" / "seed_demo_data.py"
    spec = importlib.util.spec_from_file_location("seed_demo_data", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["seed_demo_data"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_run_mukti_pipeline_persists_execution_feedback() -> None:
    from common_schemas import ExecutionStatus, FeedbackSource

    from app.adapters.repository import InMemoryRepository
    from app.services.execution_service import ExecutionService
    from feedback_service.service import FeedbackService
    from mukti_agent.service import MuktiService

    seed = _load_seed()
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    fb = FeedbackService()
    ex = exec_svc.create_execution(
        workflow_type="incident_triage",
        input_payload={"incident_id": "seed-test"},
        tenant_id="dev-tenant",
        request_id="demo-seed",
        environment="dev",
        policy_scope="default",
    )
    done = exec_svc.start_execution(ex.execution_id)
    assert done.status == ExecutionStatus.COMPLETED

    fb.submit_operator_feedback(
        execution_id=ex.execution_id,
        source=FeedbackSource.OPERATOR_CONSOLE,
        labels=["demo"],
        detail={},
    )

    out = seed.run_mukti_pipeline(
        repository=repo,
        feedback_service=fb,
        mukti_service=MuktiService(),
        execution_id=ex.execution_id,
    )
    stored = fb.list_execution_feedback_for_execution(ex.execution_id)
    assert len(stored) == 1
    assert stored[0].feedback_id == out.feedback_id
    assert stored[0].patterns_detected


def test_persist_mukti_skips_without_postgres_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    seed = _load_seed()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCHESTRATOR_DATABASE_URL", raising=False)
    monkeypatch.setenv("GATEWAY_USE_POSTGRES", "false")
    seed.persist_mukti_execution_feedback(str(uuid4()))


def test_postgres_seed_mode_with_database_url_overrides_gateway_flag_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = _load_seed()
    monkeypatch.setenv("GATEWAY_USE_POSTGRES", "false")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@postgres:5432/agentic_dev")
    assert seed._postgres_seed_mode() is True
