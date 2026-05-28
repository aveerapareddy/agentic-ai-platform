"""Replay v2: child execution, provenance, trace event, source immutability."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from common_schemas import (
    REPLAY_PROVENANCE_INPUT_KEY,
    ExecutionMode,
    ExecutionStatus,
    ReplayMode,
    ReplayRequest,
)

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService
from app.services.replay_service import ReplayService, ReplayValidationError


def _source_execution(repo: InMemoryRepository, svc: ExecutionService):
    return svc.create_execution(
        workflow_type="generic",
        input_payload={"incident_id": "src-1", "severity": "high"},
        tenant_id="t1",
        request_id="req-src",
        environment="prod",
        policy_scope="default",
        execution_mode=ExecutionMode.BACKGROUND,
    )


def test_exact_replay_creates_child_with_provenance_and_trace() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    src = _source_execution(repo, exec_svc)
    src_snapshot = src.model_dump(mode="json")

    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="post-incident",
            requested_by="operator@test",
        )
    )

    assert created.replay_execution_id != src.execution_id
    assert created.source_execution_id == src.execution_id
    assert created.replay_mode == ReplayMode.EXACT
    assert created.provenance.created_execution_id == created.replay_execution_id

    child = repo.get_execution(created.replay_execution_id)
    assert child is not None
    assert child.parent_execution_id == src.execution_id
    assert child.workflow_type == src.workflow_type
    assert child.input.get("incident_id") == "src-1"
    assert REPLAY_PROVENANCE_INPUT_KEY in child.input
    assert child.input[REPLAY_PROVENANCE_INPUT_KEY]["source_execution_id"] == str(src.execution_id)
    assert any(e.get("event_type") == "replay_created" for e in child.trace_timeline)

    src_after = repo.get_execution(src.execution_id)
    assert src_after is not None
    assert src_after.model_dump(mode="json") == src_snapshot


def test_investigative_replay_applies_input_overrides() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    src = _source_execution(repo, exec_svc)

    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.INVESTIGATIVE,
            environment_target="sandbox",
            reason="hypothesis: lower severity",
            input_overrides={"severity": "low"},
        )
    )

    child = repo.get_execution(created.replay_execution_id)
    assert child is not None
    assert child.input["severity"] == "low"
    assert created.provenance.input_overrides == {"severity": "low"}
    replay_evt = next(e for e in child.trace_timeline if e.get("event_type") == "replay_created")
    assert replay_evt["input_overrides_summary"]["keys"] == ["severity"]


def test_investigative_requires_reason_or_label() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    src = _source_execution(repo, exec_svc)

    with pytest.raises(ReplayValidationError, match="reason or label"):
        replay_svc.create_replay(
            ReplayRequest(
                source_execution_id=src.execution_id,
                replay_mode=ReplayMode.INVESTIGATIVE,
                environment_target="sandbox",
            )
        )


def test_exact_replay_rejects_input_overrides() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    src = _source_execution(repo, exec_svc)

    with pytest.raises(ReplayValidationError, match="input_overrides"):
        replay_svc.create_replay(
            ReplayRequest(
                source_execution_id=src.execution_id,
                replay_mode=ReplayMode.EXACT,
                environment_target="sandbox",
                input_overrides={"severity": "low"},
            )
        )


def test_list_replays_by_parent() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    src = _source_execution(repo, exec_svc)

    replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="r1",
        )
    )
    replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="r2",
        )
    )

    children = replay_svc.list_replays_for_source(src.execution_id, limit=10)
    assert len(children) == 2
    assert all(c.parent_execution_id == src.execution_id for c in children)
