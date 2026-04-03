"""
PostgreSQL integration tests for PostgresRepository.

Requires:
  - ORCHESTRATOR_TEST_DATABASE_URL (e.g. postgresql+psycopg://user:pass@localhost:5432/orchestrator_test)
  - Schema from infra/db/migrations/001_initial_schema.sql applied to that database, OR
  - ORCHESTRATOR_TEST_CREATE_SCHEMA=1 to create tables from SQLAlchemy models (must stay aligned with 001).

TODO: Add CI job with ephemeral Postgres and migration apply for full fidelity with CHECK constraints.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from common_schemas import (
    Execution,
    ExecutionContext,
    ExecutionMode,
    ExecutionPlan,
    ExecutionStatus,
    Step,
    StepDependency,
    StepResult,
    StepStatus,
    StepType,
    StepCompleteness,
    ValidationOutcome,
)
from sqlalchemy import text

from app.adapters.db import create_engine_from_settings, create_session_factory
from app.adapters.models import Base
from app.adapters.repository import PostgresRepository
from app.config import DatabaseSettings
from app.runtime.orchestrator import ExecutionEngine

_TEST_URL = os.environ.get("ORCHESTRATOR_TEST_DATABASE_URL")
_CREATE_SCHEMA = os.environ.get("ORCHESTRATOR_TEST_CREATE_SCHEMA", "").lower() in ("1", "true", "yes")

pytestmark = pytest.mark.skipif(
    not _TEST_URL,
    reason=(
        "Set ORCHESTRATOR_TEST_DATABASE_URL to run Postgres integration tests. "
        "Apply infra/db/migrations/001_initial_schema.sql, or set ORCHESTRATOR_TEST_CREATE_SCHEMA=1 "
        "(models must match migration)."
    ),
)


def _clear_tables(engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM step_results"))
        conn.execute(text("DELETE FROM execution_steps"))
        conn.execute(text("DELETE FROM execution_plans"))
        conn.execute(text("DELETE FROM executions"))
        conn.execute(text("DELETE FROM execution_context"))


@pytest.fixture
def pg_repo():
    settings = DatabaseSettings(url=_TEST_URL, echo_sql=False)
    engine = create_engine_from_settings(settings)
    if _CREATE_SCHEMA:
        Base.metadata.create_all(engine, checkfirst=True)
    _clear_tables(engine)
    factory = create_session_factory(engine)
    repo = PostgresRepository(factory)
    yield repo
    _clear_tables(engine)


def test_postgres_roundtrip_execution_context_plan_step_result(pg_repo: PostgresRepository) -> None:
    now = datetime.now(timezone.utc)
    cid = uuid4()
    eid = uuid4()
    pid = uuid4()
    sid = uuid4()

    ctx = ExecutionContext(
        context_id=cid,
        tenant_id="t",
        principal_id="p",
        request_id="r",
        environment="dev",
        permissions_scope={},
        policy_scope="default",
        feature_flags=None,
        created_at=now,
        updated_at=now,
    )
    pg_repo.save_context(ctx)
    assert pg_repo.get_context(cid) is not None

    ex = Execution(
        execution_id=eid,
        workflow_type="incident_triage",
        status=ExecutionStatus.CREATED,
        execution_mode=ExecutionMode.INTERACTIVE,
        execution_context_id=cid,
        input={"k": "v"},
        created_at=now,
        updated_at=now,
    )
    pg_repo.save_execution(ex)
    loaded = pg_repo.get_execution(eid)
    assert loaded is not None
    assert loaded.execution_mode == ExecutionMode.INTERACTIVE
    assert loaded.input == {"k": "v"}

    plan = ExecutionPlan(
        plan_id=pid,
        execution_id=eid,
        parent_plan_id=None,
        plan_version=1,
        revision_reason="test",
        goal={},
        steps=[{"step_key": "a", "kind": "reasoning"}],
        dependencies=[],
        ordering={},
        metadata={},
        created_at=now,
    )
    pg_repo.save_plan(plan)
    assert pg_repo.get_plan(pid) is not None

    ex2 = ex.model_copy(update={"current_plan_id": pid, "updated_at": now})
    pg_repo.update_execution(ex2)

    step = Step(
        step_id=sid,
        execution_id=eid,
        plan_id=pid,
        step_type=StepType.REASONING,
        agent="agent",
        input={},
        status=StepStatus.PENDING,
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    pg_repo.save_step(step)
    assert pg_repo.get_step(sid) is not None

    dep_step = step.model_copy(
        update={
            "dependencies": [StepDependency(step_id=sid)],
            "updated_at": now,
        }
    )
    pg_repo.update_step(dep_step)
    listed = pg_repo.list_steps_for_execution(eid)
    assert len(listed) == 1
    assert len(listed[0].dependencies) == 1

    rid = uuid4()
    result = StepResult(
        step_result_id=rid,
        step_id=sid,
        output={"ok": True},
        evidence=[],
        errors=[],
        latency_ms=5,
        latency_started_at=now,
        latency_ended_at=now,
        confidence_score=0.9,
        confidence_detail={"src": "test"},
        completeness=StepCompleteness.FULL,
        validation_outcome=ValidationOutcome(status="passed", details={}),
        created_at=now,
        updated_at=now,
    )
    pg_repo.save_step_result(result)
    got = pg_repo.get_step_result(sid)
    assert got is not None
    assert got.confidence_score == pytest.approx(0.9)
    assert got.validation_outcome is not None
    assert got.validation_outcome.status == "passed"


def test_postgres_engine_happy_path(pg_repo: PostgresRepository) -> None:
    """Full orchestration against PostgresRepository (constitution §6.1 path)."""
    now = datetime.now(timezone.utc)
    cid = uuid4()
    eid = uuid4()

    ctx = ExecutionContext(
        context_id=cid,
        tenant_id="t",
        request_id="r",
        environment="dev",
        permissions_scope={},
        policy_scope="p",
        created_at=now,
        updated_at=now,
    )
    pg_repo.save_context(ctx)
    ex = Execution(
        execution_id=eid,
        workflow_type="generic",
        status=ExecutionStatus.CREATED,
        execution_context_id=cid,
        input={},
        created_at=now,
        updated_at=now,
    )
    pg_repo.save_execution(ex)

    engine = ExecutionEngine(pg_repo)
    done = engine.run_execution(eid)
    assert done.status == ExecutionStatus.COMPLETED
    assert done.validation_summary is not None
    steps = pg_repo.list_steps_for_execution(eid)
    assert len(steps) == 2
