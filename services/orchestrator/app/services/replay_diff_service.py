"""Read-only replay comparison between source and child executions."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from common_schemas import (
    REPLAY_PROVENANCE_INPUT_KEY,
    Approval,
    Execution,
    PolicyEvaluation,
    ReplayDiffCategory,
    ReplayDiffItem,
    ReplayDiffSeverity,
    ReplayDiffSummary,
    ReplayMode,
    ReplayProvenance,
    Step,
    StepResult,
    ToolCall,
)

from app.adapters.repository import Repository


class ReplayDiffError(Exception):
    """Base replay diff failure."""


class ReplayDiffNotFoundError(ReplayDiffError):
    """Source or replay execution missing."""


# Top-level result keys compared when both sides have dict results (avoid full JSON dump).
_RESULT_KEYS_OF_INTEREST = (
    "status",
    "outcome",
    "summary",
    "validation",
    "governance",
    "error",
    "message",
)

# Step output keys compared when structured dicts exist.
_STEP_OUTPUT_KEYS_OF_INTEREST = (
    "status",
    "outcome",
    "summary",
    "severity",
    "root_cause",
    "recommendation",
)


def _brief(value: Any, *, max_len: int = 400) -> str | None:
    if value is None:
        return None
    try:
        text = json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        text = str(value)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def _business_input(execution: Execution) -> dict[str, Any]:
    raw = dict(execution.input or {})
    raw.pop(REPLAY_PROVENANCE_INPUT_KEY, None)
    return raw


def _provenance(execution: Execution) -> ReplayProvenance | None:
    raw = (execution.input or {}).get(REPLAY_PROVENANCE_INPUT_KEY)
    if not isinstance(raw, dict):
        return None
    try:
        return ReplayProvenance.model_validate(raw)
    except Exception:
        return None


def _is_linked(source: Execution, replay: Execution) -> bool:
    if replay.parent_execution_id == source.execution_id:
        return True
    prov = _provenance(replay)
    return prov is not None and prov.source_execution_id == source.execution_id


class ReplayDiffService:
    """Compares stored execution artifacts only; never mutates rows or re-runs workflows."""

    def __init__(self, repository: Repository) -> None:
        self._repo = repository

    def compare(self, source_execution_id: UUID, replay_execution_id: UUID) -> ReplayDiffSummary:
        source = self._repo.get_execution(source_execution_id)
        replay = self._repo.get_execution(replay_execution_id)
        if source is None:
            raise ReplayDiffNotFoundError(f"source execution {source_execution_id} not found")
        if replay is None:
            raise ReplayDiffNotFoundError(f"replay execution {replay_execution_id} not found")

        source_snap = source.model_dump(mode="json")
        replay_snap = replay.model_dump(mode="json")

        items: list[ReplayDiffItem] = []
        linked = _is_linked(source, replay)
        prov = _provenance(replay)
        replay_mode = prov.replay_mode if prov else None

        items.extend(self._compare_lineage(source, replay, linked, prov))
        items.extend(self._compare_execution_header(source, replay))
        items.extend(self._compare_input(source, replay, prov))
        items.extend(self._compare_plan(source, replay))
        items.extend(self._compare_steps(source, replay))
        items.extend(self._compare_model_reasoning(source, replay))
        items.extend(self._compare_tool_calls(source, replay))
        items.extend(self._compare_policy(source, replay))
        items.extend(self._compare_approvals(source, replay))
        items.extend(self._compare_validation(source, replay))
        items.extend(self._compare_result(source, replay))

        significant = sum(1 for i in items if i.severity == ReplayDiffSeverity.SIGNIFICANT)

        summary = ReplayDiffSummary(
            source_execution_id=source.execution_id,
            replay_execution_id=replay.execution_id,
            replay_mode=replay_mode,
            linked_to_source=linked,
            total_differences=len(items),
            significant_differences=significant,
            items=items,
        )

        src_after = self._repo.get_execution(source_execution_id)
        rep_after = self._repo.get_execution(replay_execution_id)
        if src_after is None or rep_after is None:
            raise ReplayDiffError("execution disappeared during read-only diff")
        if src_after.model_dump(mode="json") != source_snap:
            raise ReplayDiffError("source execution mutated during diff")
        if rep_after.model_dump(mode="json") != replay_snap:
            raise ReplayDiffError("replay execution mutated during diff")

        return summary

    def _compare_lineage(
        self,
        source: Execution,
        replay: Execution,
        linked: bool,
        prov: ReplayProvenance | None,
    ) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        if linked:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.LINEAGE,
                    severity=ReplayDiffSeverity.INFO,
                    title="linked_to_source",
                    description="Replay is linked to source via parent_execution_id and/or replay provenance.",
                    source_value=str(source.execution_id),
                    replay_value=str(replay.parent_execution_id),
                    path="lineage.parent_execution_id",
                )
            )
        else:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.LINEAGE,
                    severity=ReplayDiffSeverity.SIGNIFICANT,
                    title="not_linked_to_source",
                    description=(
                        "Replay parent_execution_id and provenance do not reference the given source execution."
                    ),
                    source_value=str(source.execution_id),
                    replay_value=str(replay.parent_execution_id),
                    path="lineage",
                )
            )
        if prov and prov.input_overrides:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.INPUT,
                    severity=ReplayDiffSeverity.INFO,
                    title="investigative_input_overrides",
                    description="Replay provenance records investigative input overrides applied at creation.",
                    source_value=None,
                    replay_value=_brief(prov.input_overrides),
                    path="provenance.input_overrides",
                )
            )
        return out

    def _compare_execution_header(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        if source.status != replay.status:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.EXECUTION_STATUS,
                    severity=ReplayDiffSeverity.SIGNIFICANT,
                    title="execution_status",
                    description="Terminal or lifecycle status differs between source and replay.",
                    source_value=source.status.value,
                    replay_value=replay.status.value,
                    path="execution.status",
                )
            )
        if source.workflow_type != replay.workflow_type:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.EXECUTION_STATUS,
                    severity=ReplayDiffSeverity.SIGNIFICANT,
                    title="workflow_type",
                    description="Workflow type differs (unexpected for replay derived from source).",
                    source_value=source.workflow_type,
                    replay_value=replay.workflow_type,
                    path="execution.workflow_type",
                )
            )
        return out

    def _compare_input(
        self,
        source: Execution,
        replay: Execution,
        prov: ReplayProvenance | None,
    ) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        src_in = _business_input(source)
        rep_in = _business_input(replay)
        all_keys = sorted(set(src_in) | set(rep_in))
        for key in all_keys:
            sv, rv = src_in.get(key), rep_in.get(key)
            if sv != rv:
                sev = ReplayDiffSeverity.WARNING
                if prov and key in prov.input_overrides:
                    sev = ReplayDiffSeverity.INFO
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.INPUT,
                        severity=sev,
                        title=f"input.{key}",
                        description=f"Business input field '{key}' differs.",
                        source_value=_brief(sv),
                        replay_value=_brief(rv),
                        path=f"input.{key}",
                    )
                )
        return out

    def _compare_plan(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        if source.current_plan_id != replay.current_plan_id:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.PLAN,
                    severity=ReplayDiffSeverity.WARNING,
                    title="current_plan_id",
                    description="Current plan revision id differs (expected when replay re-plans).",
                    source_value=str(source.current_plan_id) if source.current_plan_id else None,
                    replay_value=str(replay.current_plan_id) if replay.current_plan_id else None,
                    path="execution.current_plan_id",
                )
            )
        src_steps = self._repo.list_steps_for_execution(source.execution_id)
        rep_steps = self._repo.list_steps_for_execution(replay.execution_id)
        if len(src_steps) != len(rep_steps):
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.PLAN,
                    severity=ReplayDiffSeverity.SIGNIFICANT,
                    title="step_count",
                    description="Number of persisted steps differs between source and replay.",
                    source_value=str(len(src_steps)),
                    replay_value=str(len(rep_steps)),
                    path="steps.count",
                )
            )
        return out

    def _compare_steps(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        src_steps = sorted(
            self._repo.list_steps_for_execution(source.execution_id),
            key=lambda s: s.created_at,
        )
        rep_steps = sorted(
            self._repo.list_steps_for_execution(replay.execution_id),
            key=lambda s: s.created_at,
        )
        if not src_steps and not rep_steps:
            return out

        pair_count = max(len(src_steps), len(rep_steps))
        for idx in range(pair_count):
            path_prefix = f"steps[{idx}]"
            if idx >= len(src_steps):
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.STEP,
                        severity=ReplayDiffSeverity.SIGNIFICANT,
                        title="extra_replay_step",
                        description="Replay has a step with no positional match in source ordering.",
                        replay_value=_brief(_step_label(rep_steps[idx])),
                        path=path_prefix,
                        related_step_id=rep_steps[idx].step_id,
                    )
                )
                continue
            if idx >= len(rep_steps):
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.STEP,
                        severity=ReplayDiffSeverity.SIGNIFICANT,
                        title="missing_replay_step",
                        description="Source has a step with no positional match in replay ordering.",
                        source_value=_brief(_step_label(src_steps[idx])),
                        path=path_prefix,
                        related_step_id=src_steps[idx].step_id,
                    )
                )
                continue

            ss, rs = src_steps[idx], rep_steps[idx]
            st = ss.step_type.value if hasattr(ss.step_type, "value") else str(ss.step_type)
            rt = rs.step_type.value if hasattr(rs.step_type, "value") else str(rs.step_type)
            if st != rt:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.STEP,
                        severity=ReplayDiffSeverity.WARNING,
                        title="step_type",
                        description=f"Step type differs at index {idx} (ordered by created_at).",
                        source_value=st,
                        replay_value=rt,
                        path=f"{path_prefix}.type",
                        related_step_id=rs.step_id,
                    )
                )
            if ss.status != rs.status:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.STEP,
                        severity=ReplayDiffSeverity.WARNING,
                        title="step_status",
                        description=f"Step status differs at index {idx}.",
                        source_value=ss.status.value,
                        replay_value=rs.status.value,
                        path=f"{path_prefix}.status",
                        related_step_id=rs.step_id,
                    )
                )
            if ss.agent != rs.agent:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.STEP,
                        severity=ReplayDiffSeverity.INFO,
                        title="step_agent",
                        description=f"Step agent binding differs at index {idx}.",
                        source_value=ss.agent,
                        replay_value=rs.agent,
                        path=f"{path_prefix}.agent",
                        related_step_id=rs.step_id,
                    )
                )
            out.extend(self._compare_step_results(ss, rs, path_prefix))

        return out

    def _compare_step_results(self, source_step: Step, replay_step: Step, path_prefix: str) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        src_sr = self._repo.get_step_result(source_step.step_id)
        rep_sr = self._repo.get_step_result(replay_step.step_id)
        if src_sr is None and rep_sr is None:
            return out
        if src_sr is None or rep_sr is None:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.STEP,
                    severity=ReplayDiffSeverity.WARNING,
                    title="step_result_presence",
                    description="Step result exists on one side only.",
                    source_value="present" if src_sr else "absent",
                    replay_value="present" if rep_sr else "absent",
                    path=f"{path_prefix}.result",
                    related_step_id=replay_step.step_id,
                )
            )
            return out

        if src_sr.completeness != rep_sr.completeness:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.STEP,
                    severity=ReplayDiffSeverity.WARNING,
                    title="completeness",
                    description="Step result completeness differs.",
                    source_value=str(src_sr.completeness) if src_sr.completeness else None,
                    replay_value=str(rep_sr.completeness) if rep_sr.completeness else None,
                    path=f"{path_prefix}.result.completeness",
                    related_step_id=replay_step.step_id,
                )
            )
        if src_sr.confidence_score != rep_sr.confidence_score:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.STEP,
                    severity=ReplayDiffSeverity.INFO,
                    title="confidence_score",
                    description="Advisory confidence score differs.",
                    source_value=str(src_sr.confidence_score),
                    replay_value=str(rep_sr.confidence_score),
                    path=f"{path_prefix}.result.confidence_score",
                    related_step_id=replay_step.step_id,
                )
            )
        vo_s = src_sr.validation_outcome.status if src_sr.validation_outcome else None
        vo_r = rep_sr.validation_outcome.status if rep_sr.validation_outcome else None
        if vo_s != vo_r:
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.VALIDATION,
                    severity=ReplayDiffSeverity.WARNING,
                    title="step_validation_outcome",
                    description="Step-level validation outcome status differs.",
                    source_value=vo_s,
                    replay_value=vo_r,
                    path=f"{path_prefix}.result.validation_outcome.status",
                    related_step_id=replay_step.step_id,
                )
            )
        out.extend(
            self._compare_dict_fields(
                src_sr.output,
                rep_sr.output,
                category=ReplayDiffCategory.STEP,
                path_prefix=f"{path_prefix}.result.output",
                keys=_STEP_OUTPUT_KEYS_OF_INTEREST,
                related_step_id=replay_step.step_id,
            )
        )
        return out

    def _compare_model_reasoning(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        src_events = [e for e in source.trace_timeline if e.get("event_type") == "model_reasoning"]
        rep_events = [e for e in replay.trace_timeline if e.get("event_type") == "model_reasoning"]
        if not src_events and not rep_events:
            return out
        if len(src_events) != len(rep_events):
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.MODEL_REASONING,
                    severity=ReplayDiffSeverity.WARNING,
                    title="model_reasoning_event_count",
                    description="Count of model_reasoning trace events differs.",
                    source_value=str(len(src_events)),
                    replay_value=str(len(rep_events)),
                    path="trace_timeline.model_reasoning.count",
                )
            )
        for idx, (se, re) in enumerate(zip(src_events, rep_events, strict=False)):
            sp, rp = se.get("path"), re.get("path")
            if sp != rp:
                sev = ReplayDiffSeverity.SIGNIFICANT
                if {sp, rp} <= {"model_runtime", "deterministic_fallback"}:
                    sev = ReplayDiffSeverity.WARNING
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.MODEL_REASONING,
                        severity=sev,
                        title="model_path",
                        description=f"model_reasoning path differs at event index {idx}.",
                        source_value=str(sp),
                        replay_value=str(rp),
                        path=f"trace_timeline.model_reasoning[{idx}].path",
                    )
                )
            st, rt = se.get("task"), re.get("task")
            if st != rt:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.MODEL_REASONING,
                        severity=ReplayDiffSeverity.INFO,
                        title="model_task",
                        description=f"model_reasoning task differs at event index {idx}.",
                        source_value=str(st),
                        replay_value=str(rt),
                        path=f"trace_timeline.model_reasoning[{idx}].task",
                    )
                )
        return out

    def _compare_tool_calls(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        src_calls = self._all_tool_calls(source.execution_id)
        rep_calls = self._all_tool_calls(replay.execution_id)
        if not src_calls and not rep_calls:
            return out
        if len(src_calls) != len(rep_calls):
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.TOOL_CALL,
                    severity=ReplayDiffSeverity.WARNING,
                    title="tool_call_count",
                    description="Total tool call count differs (flattened across steps by created_at).",
                    source_value=str(len(src_calls)),
                    replay_value=str(len(rep_calls)),
                    path="tool_calls.count",
                )
            )
        for idx, (sc, rc) in enumerate(zip(src_calls, rep_calls, strict=False)):
            prefix = f"tool_calls[{idx}]"
            if sc.tool_name != rc.tool_name:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.TOOL_CALL,
                        severity=ReplayDiffSeverity.WARNING,
                        title="tool_name",
                        description=f"Tool name differs at index {idx}.",
                        source_value=sc.tool_name,
                        replay_value=rc.tool_name,
                        path=f"{prefix}.tool_name",
                        related_tool_call_id=rc.tool_call_id,
                    )
                )
            if sc.status != rc.status:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.TOOL_CALL,
                        severity=ReplayDiffSeverity.WARNING,
                        title="tool_call_status",
                        description=f"Tool call status differs at index {idx}.",
                        source_value=sc.status.value,
                        replay_value=rc.status.value,
                        path=f"{prefix}.status",
                        related_tool_call_id=rc.tool_call_id,
                    )
                )
            if sc.side_effect_class != rc.side_effect_class:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.TOOL_CALL,
                        severity=ReplayDiffSeverity.INFO,
                        title="side_effect_class",
                        description="Tool side-effect class differs.",
                        source_value=sc.side_effect_class.value,
                        replay_value=rc.side_effect_class.value,
                        path=f"{prefix}.side_effect_class",
                        related_tool_call_id=rc.tool_call_id,
                    )
                )
            if sc.idempotency != rc.idempotency:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.TOOL_CALL,
                        severity=ReplayDiffSeverity.INFO,
                        title="idempotency",
                        description="Tool idempotency declaration differs.",
                        source_value=sc.idempotency.value,
                        replay_value=rc.idempotency.value,
                        path=f"{prefix}.idempotency",
                        related_tool_call_id=rc.tool_call_id,
                    )
                )
        return out

    def _compare_policy(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        src_evals = self._repo.list_policy_evaluations_for_execution(source.execution_id)
        rep_evals = self._repo.list_policy_evaluations_for_execution(replay.execution_id)
        if not src_evals and not rep_evals:
            return out
        if len(src_evals) != len(rep_evals):
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.POLICY,
                    severity=ReplayDiffSeverity.WARNING,
                    title="policy_evaluation_count",
                    description="Number of policy evaluations differs.",
                    source_value=str(len(src_evals)),
                    replay_value=str(len(rep_evals)),
                    path="policy_evaluations.count",
                )
            )
        for idx, (se, re) in enumerate(zip(src_evals, rep_evals, strict=False)):
            if se.decision != re.decision:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.POLICY,
                        severity=ReplayDiffSeverity.SIGNIFICANT,
                        title="policy_decision",
                        description=f"Policy decision differs at evaluation index {idx}.",
                        source_value=se.decision.value,
                        replay_value=re.decision.value,
                        path=f"policy_evaluations[{idx}].decision",
                    )
                )
            elif se.reason != re.reason:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.POLICY,
                        severity=ReplayDiffSeverity.INFO,
                        title="policy_reason",
                        description=f"Policy reason text differs at evaluation index {idx}.",
                        source_value=_brief(se.reason, max_len=200),
                        replay_value=_brief(re.reason, max_len=200),
                        path=f"policy_evaluations[{idx}].reason",
                    )
                )
        src_props = self._repo.list_action_proposals_for_execution(source.execution_id)
        rep_props = self._repo.list_action_proposals_for_execution(replay.execution_id)
        if src_props or rep_props:
            if len(src_props) != len(rep_props):
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.POLICY,
                        severity=ReplayDiffSeverity.INFO,
                        title="action_proposal_count",
                        description="Action proposal count differs.",
                        source_value=str(len(src_props)),
                        replay_value=str(len(rep_props)),
                        path="action_proposals.count",
                    )
                )
        return out

    def _compare_approvals(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        src_ap = self._repo.list_approvals_for_execution(source.execution_id)
        rep_ap = self._repo.list_approvals_for_execution(replay.execution_id)
        if not src_ap and not rep_ap:
            return out
        if len(src_ap) != len(rep_ap):
            out.append(
                ReplayDiffItem(
                    category=ReplayDiffCategory.POLICY,
                    severity=ReplayDiffSeverity.WARNING,
                    title="approval_count",
                    description="Number of approval records differs.",
                    source_value=str(len(src_ap)),
                    replay_value=str(len(rep_ap)),
                    path="approvals.count",
                )
            )
        for idx, (sa, ra) in enumerate(zip(src_ap, rep_ap, strict=False)):
            if sa.decision != ra.decision:
                out.append(
                    ReplayDiffItem(
                        category=ReplayDiffCategory.POLICY,
                        severity=ReplayDiffSeverity.SIGNIFICANT,
                        title="approval_decision",
                        description=f"Approval decision differs at index {idx}.",
                        source_value=sa.decision.value,
                        replay_value=ra.decision.value,
                        path=f"approvals[{idx}].decision",
                    )
                )
        return out

    def _compare_validation(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        if source.validation_summary == replay.validation_summary:
            return out
        if source.validation_summary is None and replay.validation_summary is None:
            return out
        out.append(
            ReplayDiffItem(
                category=ReplayDiffCategory.VALIDATION,
                severity=ReplayDiffSeverity.WARNING,
                title="validation_summary",
                description="Execution-level validation_summary differs.",
                source_value=_brief(source.validation_summary),
                replay_value=_brief(replay.validation_summary),
                path="execution.validation_summary",
            )
        )
        return out

    def _compare_result(self, source: Execution, replay: Execution) -> list[ReplayDiffItem]:
        if source.result is None and replay.result is None:
            return []
        if source.result is None or replay.result is None:
            return [
                ReplayDiffItem(
                    category=ReplayDiffCategory.RESULT,
                    severity=ReplayDiffSeverity.WARNING,
                    title="result_presence",
                    description="Top-level execution result present on one side only.",
                    source_value="present" if source.result else "absent",
                    replay_value="present" if replay.result else "absent",
                    path="execution.result",
                )
            ]
        return self._compare_dict_fields(
            source.result,
            replay.result,
            category=ReplayDiffCategory.RESULT,
            path_prefix="execution.result",
            keys=_RESULT_KEYS_OF_INTEREST,
            severity=ReplayDiffSeverity.WARNING,
        )

    def _compare_dict_fields(
        self,
        source: dict[str, Any] | None,
        replay: dict[str, Any] | None,
        *,
        category: ReplayDiffCategory,
        path_prefix: str,
        keys: tuple[str, ...],
        related_step_id: UUID | None = None,
        severity: ReplayDiffSeverity = ReplayDiffSeverity.INFO,
    ) -> list[ReplayDiffItem]:
        out: list[ReplayDiffItem] = []
        if not isinstance(source, dict) or not isinstance(replay, dict):
            return out
        for key in keys:
            if key not in source and key not in replay:
                continue
            sv, rv = source.get(key), replay.get(key)
            if sv != rv:
                out.append(
                    ReplayDiffItem(
                        category=category,
                        severity=severity,
                        title=key,
                        description=f"Field '{key}' differs under {path_prefix}.",
                        source_value=_brief(sv),
                        replay_value=_brief(rv),
                        path=f"{path_prefix}.{key}",
                        related_step_id=related_step_id,
                    )
                )
        return out

    def _all_tool_calls(self, execution_id: UUID) -> list[ToolCall]:
        calls: list[ToolCall] = []
        steps = sorted(
            self._repo.list_steps_for_execution(execution_id),
            key=lambda s: s.created_at,
        )
        for step in steps:
            calls.extend(self._repo.list_tool_calls_for_step(step.step_id))
        calls.sort(key=lambda c: c.created_at)
        return calls


def _step_label(step: Step) -> dict[str, Any]:
    st = step.step_type.value if hasattr(step.step_type, "value") else str(step.step_type)
    return {"step_id": str(step.step_id), "type": st, "status": step.status.value, "agent": step.agent}
