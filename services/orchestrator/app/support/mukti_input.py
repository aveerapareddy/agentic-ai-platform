"""Build frozen MuktiAnalysisInput from persisted execution state (post-termination reads only)."""

from __future__ import annotations

from uuid import UUID

from common_schemas import MuktiAnalysisInput, OperatorFeedback, StepRunRecord

from app.adapters.repository import Repository


def build_mukti_analysis_input(
    repo: Repository,
    execution_id: UUID,
    *,
    operator_feedback: list[OperatorFeedback] | None = None,
) -> MuktiAnalysisInput:
    """Load execution graph for Mukti; does not invoke mukti-agent or mutate runs."""
    ex = repo.get_execution(execution_id)
    if ex is None:
        msg = f"execution not found: {execution_id}"
        raise KeyError(msg)
    steps = repo.list_steps_for_execution(execution_id)
    records = [StepRunRecord(step=s, result=repo.get_step_result(s.step_id)) for s in steps]
    return MuktiAnalysisInput(
        execution=ex,
        step_records=records,
        operator_feedback=list(operator_feedback or []),
        policy_evaluations=repo.list_policy_evaluations_for_execution(execution_id),
        action_proposals=repo.list_action_proposals_for_execution(execution_id),
    )
