"""Replay diff engine: read-only, deterministic comparisons."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from common_schemas import (
    ExecutionMode,
    ExecutionStatus,
    ReplayDiffCategory,
    ReplayDiffSeverity,
    ReplayMode,
    ReplayRequest,
    Step,
    StepCompleteness,
    StepResult,
    StepStatus,
    StepType,
    ToolCallStatus,
    ToolIdempotency,
    ToolSideEffectClass,
)
from common_schemas.ids import ContextId
from common_schemas.tooling import ToolCall

from app.adapters.repository import InMemoryRepository
from app.services.execution_service import ExecutionService
from app.services.replay_diff_service import ReplayDiffService
from app.services.replay_service import ReplayService


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _source(repo: InMemoryRepository, svc: ExecutionService):
    ex = svc.create_execution(
        workflow_type="generic",
        input_payload={"incident_id": "a", "severity": "high"},
        tenant_id="t1",
        request_id="r1",
        environment="prod",
        policy_scope="default",
        execution_mode=ExecutionMode.BACKGROUND,
    )
    ex = ex.model_copy(update={"status": ExecutionStatus.COMPLETED, "result": {"outcome": "ok"}})
    repo.update_execution(ex)
    return ex


def test_exact_linked_replay_minimal_input_diff_only_provenance() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    diff_svc = ReplayDiffService(repo)
    src = _source(repo, exec_svc)
    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="unit",
        )
    )
    summary = diff_svc.compare(src.execution_id, created.replay_execution_id)
    assert summary.linked_to_source is True
    assert summary.replay_mode == ReplayMode.EXACT
    assert not any(i.severity == ReplayDiffSeverity.SIGNIFICANT and i.title == "not_linked_to_source" for i in summary.items)
    input_diffs = [i for i in summary.items if i.category == ReplayDiffCategory.INPUT and i.title.startswith("input.")]
    assert not input_diffs


def test_investigative_replay_reports_input_difference() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    diff_svc = ReplayDiffService(repo)
    src = _source(repo, exec_svc)
    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.INVESTIGATIVE,
            environment_target="sandbox",
            reason="test override",
            input_overrides={"severity": "low"},
        )
    )
    summary = diff_svc.compare(src.execution_id, created.replay_execution_id)
    sev_item = next(i for i in summary.items if i.title == "input.severity")
    assert sev_item.source_value is not None
    assert "low" in (sev_item.replay_value or "")


def test_unlinked_replay_flagged() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    diff_svc = ReplayDiffService(repo)
    src = _source(repo, exec_svc)
    other = exec_svc.create_execution(
        workflow_type="generic",
        input_payload={},
        tenant_id="t1",
        request_id="r2",
        environment="prod",
        policy_scope="default",
    )
    summary = diff_svc.compare(src.execution_id, other.execution_id)
    assert summary.linked_to_source is False
    assert any(i.title == "not_linked_to_source" for i in summary.items)


def test_status_and_result_differences_detected() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    diff_svc = ReplayDiffService(repo)
    src = _source(repo, exec_svc)
    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="x",
        )
    )
    replay_ex = repo.get_execution(created.replay_execution_id)
    assert replay_ex is not None
    replay_ex = replay_ex.model_copy(
        update={"status": ExecutionStatus.FAILED, "result": {"outcome": "failed"}}
    )
    repo.update_execution(replay_ex)

    summary = diff_svc.compare(src.execution_id, created.replay_execution_id)
    assert any(i.title == "execution_status" for i in summary.items)
    assert any(i.path == "execution.result.outcome" for i in summary.items)


def test_model_fallback_path_difference() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    diff_svc = ReplayDiffService(repo)
    now = _now()
    src = _source(repo, exec_svc)
    src = src.model_copy(
        update={
            "trace_timeline": [
                {
                    "event_type": "model_reasoning",
                    "at": now.isoformat(),
                    "path": "model_runtime",
                    "task": "analyze_incident",
                }
            ]
        }
    )
    repo.update_execution(src)
    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="mr",
        )
    )
    replay_ex = repo.get_execution(created.replay_execution_id)
    assert replay_ex is not None
    replay_ex = replay_ex.model_copy(
        update={
            "trace_timeline": [
                *replay_ex.trace_timeline,
                {
                    "event_type": "model_reasoning",
                    "at": now.isoformat(),
                    "path": "deterministic_fallback",
                    "task": "analyze_incident",
                },
            ]
        }
    )
    repo.update_execution(replay_ex)

    summary = diff_svc.compare(src.execution_id, created.replay_execution_id)
    assert any(i.category == ReplayDiffCategory.MODEL_REASONING and i.title == "model_path" for i in summary.items)


def test_step_and_tool_call_differences() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    diff_svc = ReplayDiffService(repo)
    now = _now()
    plan_id = uuid4()
    ctx_id: ContextId = uuid4()

    src = _source(repo, exec_svc)
    step = Step(
        step_id=uuid4(),
        execution_id=src.execution_id,
        plan_id=plan_id,
        step_type=StepType.REASONING,
        agent="agent_a",
        status=StepStatus.SUCCEEDED,
        created_at=now,
        updated_at=now,
    )
    repo.save_step(step)
    repo.save_step_result(
        StepResult(
            step_result_id=uuid4(),
            step_id=step.step_id,
            output={"summary": "src"},
            completeness=StepCompleteness.FULL,
            created_at=now,
            updated_at=now,
        )
    )
    repo.save_tool_call(
        ToolCall(
            tool_call_id=uuid4(),
            execution_id=src.execution_id,
            step_id=step.step_id,
            execution_context_id=ctx_id,
            tool_name="lookup",
            side_effect_class=ToolSideEffectClass.READ_ONLY,
            idempotency=ToolIdempotency.IDEMPOTENT,
            input={},
            status=ToolCallStatus.SUCCESS,
            created_at=now,
            updated_at=now,
        )
    )

    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="steps",
        )
    )
    replay_step = Step(
        step_id=uuid4(),
        execution_id=created.replay_execution_id,
        plan_id=plan_id,
        step_type=StepType.REASONING,
        agent="agent_a",
        status=StepStatus.FAILED,
        created_at=now,
        updated_at=now,
    )
    repo.save_step(replay_step)
    repo.save_step_result(
        StepResult(
            step_result_id=uuid4(),
            step_id=replay_step.step_id,
            output={"summary": "replay"},
            completeness=StepCompleteness.PARTIAL,
            created_at=now,
            updated_at=now,
        )
    )

    summary = diff_svc.compare(src.execution_id, created.replay_execution_id)
    assert any(i.title == "step_status" for i in summary.items)
    assert any(i.path.endswith("result.output.summary") for i in summary.items)


def test_executions_not_mutated_during_diff() -> None:
    repo = InMemoryRepository()
    exec_svc = ExecutionService(repo)
    replay_svc = ReplayService(repo, exec_svc)
    diff_svc = ReplayDiffService(repo)
    src = _source(repo, exec_svc)
    created = replay_svc.create_replay(
        ReplayRequest(
            source_execution_id=src.execution_id,
            replay_mode=ReplayMode.EXACT,
            environment_target="sandbox",
            label="immut",
        )
    )
    src_before = repo.get_execution(src.execution_id).model_dump(mode="json")
    rep_before = repo.get_execution(created.replay_execution_id).model_dump(mode="json")
    diff_svc.compare(src.execution_id, created.replay_execution_id)
    assert repo.get_execution(src.execution_id).model_dump(mode="json") == src_before
    assert repo.get_execution(created.replay_execution_id).model_dump(mode="json") == rep_before
