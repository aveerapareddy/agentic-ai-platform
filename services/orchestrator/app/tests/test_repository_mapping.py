"""Pure mapping helpers for PostgresRepository (no database required)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import (
    Execution,
    ExecutionMode,
    ExecutionStatus,
    StepDependency,
)

from app.adapters.repository import (
    _ORCH_EXECUTION_MODE_KEY,
    _dependencies_from_json,
    _dependencies_to_json,
    _persist_execution_input,
    _restore_execution_input_and_mode,
)


def test_execution_mode_roundtrip_via_reserved_input_key() -> None:
    now = datetime.now(timezone.utc)
    eid = uuid4()
    cid = uuid4()
    ex = Execution(
        execution_id=eid,
        workflow_type="w",
        status=ExecutionStatus.CREATED,
        execution_mode=ExecutionMode.INTERACTIVE,
        execution_context_id=cid,
        input={"user": "payload"},
        created_at=now,
        updated_at=now,
    )
    blob = _persist_execution_input(ex)
    clean, mode = _restore_execution_input_and_mode(blob)
    assert clean == {"user": "payload"}
    assert mode == ExecutionMode.INTERACTIVE


def test_dependencies_json_roundtrip() -> None:
    a, b = uuid4(), uuid4()
    deps = [StepDependency(step_id=a), StepDependency(step_id=b)]
    raw = _dependencies_to_json(deps)
    back = _dependencies_from_json(raw)
    assert [d.step_id for d in back] == [a, b]


def test_restore_execution_mode_defaults_when_missing() -> None:
    clean, mode = _restore_execution_input_and_mode({"only": "data"})
    assert clean == {"only": "data"}
    assert mode == ExecutionMode.BACKGROUND


def test_restore_invalid_mode_falls_back() -> None:
    raw = {"a": 1, _ORCH_EXECUTION_MODE_KEY: "not_a_mode"}
    clean, mode = _restore_execution_input_and_mode(raw)
    assert clean == {"a": 1}
    assert mode == ExecutionMode.BACKGROUND
