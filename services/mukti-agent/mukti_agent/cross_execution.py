"""Deterministic cross-execution Mukti v2 analysis over stored execution_feedback rows."""

from __future__ import annotations

from collections import Counter, defaultdict
from uuid import NAMESPACE_URL, UUID, uuid5

from common_schemas import (
    CrossExecutionInsight,
    ExecutionFeedback,
    ExecutionStatus,
    ExecutionSummary,
    InsightCategory,
    InsightSeverity,
    MuktiCrossExecutionInput,
    MuktiInsightsSummary,
    RankedImprovementSuggestion,
)

# Explicit thresholds (documented constants — not learned weights).
SEVERITY_ELEVATED_MIN_EVIDENCE = 5
SEVERITY_WARNING_MIN_EVIDENCE = 2
UNSTABLE_WORKFLOW_MIN_FEEDBACK = 2
UNSTABLE_WORKFLOW_FAILURE_RATE = 0.5
UNSTABLE_STEP_MIN_EXECUTIONS = 2
TOP_FAILURE_TYPES_LIMIT = 10
TOP_PATTERNS_LIMIT = 10
POLICY_FRICTION_LIMIT = 8
MODEL_FALLBACK_LIMIT = 8
UNSTABLE_LIMIT = 8
RANKED_SUGGESTIONS_LIMIT = 15

_POLICY_FAILURE_MARKERS = (
    "policy_evaluation_deny",
    "trace_policy_denied",
    "action_proposal_policy_denied",
)
_MODEL_FALLBACK_PATTERN = "model_deterministic_fallback"


def _severity_for_count(count: int) -> InsightSeverity:
    if count >= SEVERITY_ELEVATED_MIN_EVIDENCE:
        return InsightSeverity.ELEVATED
    if count >= SEVERITY_WARNING_MIN_EVIDENCE:
        return InsightSeverity.WARNING
    return InsightSeverity.INFO


def _insight_uuid(category: InsightCategory, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"mukti-v2:{category.value}:{key}")


class CrossExecutionAnalyzer:
    """Advisory rollup only; does not call orchestrator or mutate executions."""

    def analyze(self, inp: MuktiCrossExecutionInput) -> MuktiInsightsSummary:
        feedback = list(inp.execution_feedback)
        summaries = {s.execution_id: s for s in inp.execution_summaries}

        if not feedback:
            return MuktiInsightsSummary(
                scope_description="No execution_feedback rows in scope.",
                execution_feedback_sample_size=0,
            )

        wf_by_exec = {
            fb.execution_id: summaries[fb.execution_id].workflow_type
            for fb in feedback
            if fb.execution_id in summaries
        }

        scope = (
            f"Cross-execution analysis over {len(feedback)} execution_feedback row(s) "
            f"with {len(summaries)} execution summary projection(s)."
        )

        top_failures = self._top_failure_types(feedback, wf_by_exec)
        recurring = self._recurring_patterns(feedback, wf_by_exec)
        policy = self._policy_friction(feedback, wf_by_exec)
        fallback = self._model_fallback_concentration(feedback, wf_by_exec)
        unstable = self._unstable_workflows_and_steps(feedback, wf_by_exec, summaries)
        ranked = self._ranked_suggestions(feedback, wf_by_exec)

        all_insights = (
            top_failures
            + recurring
            + policy
            + fallback
            + unstable
        )

        return MuktiInsightsSummary(
            scope_description=scope,
            execution_feedback_sample_size=len(feedback),
            top_failure_types=top_failures,
            recurring_patterns=recurring,
            policy_friction_areas=policy,
            model_fallback_concentration=fallback,
            unstable_workflows_or_steps=unstable,
            ranked_improvement_suggestions=ranked,
            insights=all_insights,
        )

    def _top_failure_types(
        self,
        feedback: list[ExecutionFeedback],
        wf_by_exec: dict,
    ) -> list[CrossExecutionInsight]:
        tally: Counter[str] = Counter()
        execs_by_type: dict[str, list] = defaultdict(list)
        wf_by_type: dict[str, set[str]] = defaultdict(set)

        for fb in feedback:
            for ft in fb.failure_types:
                tally[ft] += 1
                if fb.execution_id not in execs_by_type[ft]:
                    execs_by_type[ft].append(fb.execution_id)
                wf = wf_by_exec.get(fb.execution_id)
                if wf:
                    wf_by_type[ft].add(wf)

        out: list[CrossExecutionInsight] = []
        for ft, count in tally.most_common(TOP_FAILURE_TYPES_LIMIT):
            sev = _severity_for_count(count)
            out.append(
                CrossExecutionInsight(
                    insight_id=_insight_uuid(InsightCategory.TOP_FAILURE_TYPE, ft),
                    category=InsightCategory.TOP_FAILURE_TYPE,
                    severity=sev,
                    title=ft,
                    description=(
                        f"Failure type '{ft}' appears in {count} execution_feedback row(s) "
                        f"across {len(wf_by_type[ft])} workflow type(s)."
                    ),
                    evidence_count=count,
                    affected_workflows=sorted(wf_by_type[ft])[:32],
                    affected_steps=[],
                    suggested_action=f"Investigate root cause for failure type '{ft}' in affected workflows.",
                    related_execution_ids=execs_by_type[ft][:200],
                    rank_score=count * 10,
                    evidence={"failure_type": ft, "feedback_row_hits": count},
                )
            )
        return out

    def _recurring_patterns(
        self,
        feedback: list[ExecutionFeedback],
        wf_by_exec: dict,
    ) -> list[CrossExecutionInsight]:
        tally: Counter[str] = Counter()
        execs_by_pt: dict[str, list] = defaultdict(list)
        wf_by_pt: dict[str, set[str]] = defaultdict(set)

        for fb in feedback:
            for pat in fb.patterns_detected:
                tally[pat.pattern_type] += 1
                if fb.execution_id not in execs_by_pt[pat.pattern_type]:
                    execs_by_pt[pat.pattern_type].append(fb.execution_id)
                wf = wf_by_exec.get(fb.execution_id)
                if wf:
                    wf_by_pt[pat.pattern_type].add(wf)

        out: list[CrossExecutionInsight] = []
        for pt, count in tally.most_common(TOP_PATTERNS_LIMIT):
            if count < 2:
                continue
            out.append(
                CrossExecutionInsight(
                    insight_id=_insight_uuid(InsightCategory.RECURRING_PATTERN, pt),
                    category=InsightCategory.RECURRING_PATTERN,
                    severity=_severity_for_count(count),
                    title=pt,
                    description=(
                        f"Pattern '{pt}' recurs in {count} execution_feedback row(s) "
                        f"(minimum 2 required for cross-execution flag)."
                    ),
                    evidence_count=count,
                    affected_workflows=sorted(wf_by_pt[pt])[:32],
                    affected_steps=[],
                    suggested_action=f"Review trace evidence for recurring pattern '{pt}'.",
                    related_execution_ids=execs_by_pt[pt][:200],
                    rank_score=count * 8,
                    evidence={"pattern_type": pt, "feedback_row_hits": count},
                )
            )
        return out

    def _policy_friction(
        self,
        feedback: list[ExecutionFeedback],
        wf_by_exec: dict,
    ) -> list[CrossExecutionInsight]:
        tally: Counter[str] = Counter()
        execs: dict[str, list] = defaultdict(list)
        wf_sets: dict[str, set[str]] = defaultdict(set)

        for fb in feedback:
            for ft in fb.failure_types:
                if any(m in ft for m in _POLICY_FAILURE_MARKERS) or "policy" in ft.lower():
                    tally[ft] += 1
                    if fb.execution_id not in execs[ft]:
                        execs[ft].append(fb.execution_id)
                    wf = wf_by_exec.get(fb.execution_id)
                    if wf:
                        wf_sets[ft].add(wf)
            for sug in fb.improvement_suggestions:
                if sug.category == "policy_rule":
                    key = f"suggestion:{sug.summary[:80]}"
                    tally[key] += 1
                    if fb.execution_id not in execs[key]:
                        execs[key].append(fb.execution_id)
                    wf = wf_by_exec.get(fb.execution_id)
                    if wf:
                        wf_sets[key].add(wf)

        out: list[CrossExecutionInsight] = []
        for key, count in tally.most_common(POLICY_FRICTION_LIMIT):
            title = key if not key.startswith("suggestion:") else key.removeprefix("suggestion:")
            out.append(
                CrossExecutionInsight(
                    insight_id=_insight_uuid(InsightCategory.POLICY_FRICTION, key),
                    category=InsightCategory.POLICY_FRICTION,
                    severity=_severity_for_count(count),
                    title=title[:256],
                    description=(
                        f"Policy friction signal '{title}' observed in {count} "
                        f"execution_feedback row(s)."
                    ),
                    evidence_count=count,
                    affected_workflows=sorted(wf_sets[key])[:32],
                    affected_steps=[],
                    suggested_action="Align workflow intent with policy pack; review deny and conditional rules.",
                    related_execution_ids=execs[key][:200],
                    rank_score=count * 12,
                    evidence={"signal_key": key, "feedback_row_hits": count},
                )
            )
        return out

    def _model_fallback_concentration(
        self,
        feedback: list[ExecutionFeedback],
        wf_by_exec: dict,
    ) -> list[CrossExecutionInsight]:
        wf_counts: Counter[str] = Counter()
        execs: list = []
        step_ids: set[str] = set()

        for fb in feedback:
            hit = False
            for pat in fb.patterns_detected:
                if pat.pattern_type == _MODEL_FALLBACK_PATTERN:
                    hit = True
                    sid = pat.evidence.get("step_id")
                    if isinstance(sid, str):
                        step_ids.add(sid)
            if hit:
                if fb.execution_id not in execs:
                    execs.append(fb.execution_id)
                wf = wf_by_exec.get(fb.execution_id)
                if wf:
                    wf_counts[wf] += 1

        if not execs:
            return []

        total_hits = len(execs)
        out: list[CrossExecutionInsight] = []
        for wf, count in wf_counts.most_common(MODEL_FALLBACK_LIMIT):
            out.append(
                CrossExecutionInsight(
                    insight_id=_insight_uuid(InsightCategory.MODEL_FALLBACK, f"wf:{wf}"),
                    category=InsightCategory.MODEL_FALLBACK,
                    severity=_severity_for_count(count),
                    title=f"model_fallback_in_{wf}",
                    description=(
                        f"Workflow '{wf}' has {count} execution(s) with "
                        f"'{_MODEL_FALLBACK_PATTERN}' in Mukti feedback."
                    ),
                    evidence_count=count,
                    affected_workflows=[wf],
                    affected_steps=sorted(step_ids)[:64],
                    suggested_action="Review model-runtime availability and step tasks using deterministic fallback.",
                    related_execution_ids=[e for e in execs if wf_by_exec.get(e) == wf][:200],
                    rank_score=count * 9,
                    evidence={
                        "pattern_type": _MODEL_FALLBACK_PATTERN,
                        "workflow_type": wf,
                        "execution_hits": count,
                    },
                )
            )

        if total_hits >= 2 and not wf_counts:
            out.append(
                CrossExecutionInsight(
                    insight_id=_insight_uuid(InsightCategory.MODEL_FALLBACK, "global"),
                    category=InsightCategory.MODEL_FALLBACK,
                    severity=_severity_for_count(total_hits),
                    title="model_fallback_spread",
                    description=(
                        f"{total_hits} execution(s) recorded model deterministic fallback "
                        f"without workflow projections."
                    ),
                    evidence_count=total_hits,
                    affected_workflows=[],
                    affected_steps=sorted(step_ids)[:64],
                    suggested_action="Inspect model-runtime errors in trace timeline events.",
                    related_execution_ids=execs[:200],
                    rank_score=total_hits * 9,
                    evidence={"pattern_type": _MODEL_FALLBACK_PATTERN, "execution_hits": total_hits},
                )
            )
        return out

    def _unstable_workflows_and_steps(
        self,
        feedback: list[ExecutionFeedback],
        wf_by_exec: dict,
        summaries: dict,
    ) -> list[CrossExecutionInsight]:
        wf_feedback: dict[str, list[ExecutionFeedback]] = defaultdict(list)
        for fb in feedback:
            wf = wf_by_exec.get(fb.execution_id)
            if wf:
                wf_feedback[wf].append(fb)

        out: list[CrossExecutionInsight] = []
        for wf, rows in wf_feedback.items():
            if len(rows) < UNSTABLE_WORKFLOW_MIN_FEEDBACK:
                continue
            failed = sum(
                1
                for fb in rows
                if summaries.get(fb.execution_id)
                and summaries[fb.execution_id].status
                in (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED)
            )
            rate = failed / len(rows)
            if rate < UNSTABLE_WORKFLOW_FAILURE_RATE:
                continue
            exec_ids = [fb.execution_id for fb in rows]
            out.append(
                CrossExecutionInsight(
                    insight_id=_insight_uuid(InsightCategory.UNSTABLE_WORKFLOW, wf),
                    category=InsightCategory.UNSTABLE_WORKFLOW,
                    severity=_severity_for_count(len(rows)),
                    title=f"unstable_workflow:{wf}",
                    description=(
                        f"Workflow '{wf}' shows {failed}/{len(rows)} failed/cancelled executions "
                        f"in feedback sample (rate {rate:.0%}, threshold {UNSTABLE_WORKFLOW_FAILURE_RATE:.0%})."
                    ),
                    evidence_count=len(rows),
                    affected_workflows=[wf],
                    affected_steps=[],
                    suggested_action="Stabilize workflow validation and policy paths for this workflow type.",
                    related_execution_ids=exec_ids[:200],
                    rank_score=int(rate * 100) + len(rows),
                    evidence={
                        "workflow_type": wf,
                        "failed_or_cancelled": failed,
                        "sample_size": len(rows),
                        "failure_rate": rate,
                    },
                )
            )

        step_execs: dict[str, set] = defaultdict(set)
        for fb in feedback:
            for pat in fb.patterns_detected:
                sid = pat.evidence.get("step_id")
                if isinstance(sid, str):
                    step_execs[sid].add(fb.execution_id)

        for sid, exec_set in sorted(step_execs.items(), key=lambda x: -len(x[1]))[:UNSTABLE_LIMIT]:
            if len(exec_set) < UNSTABLE_STEP_MIN_EXECUTIONS:
                continue
            wfs = sorted({wf_by_exec[e] for e in exec_set if e in wf_by_exec})[:32]
            out.append(
                CrossExecutionInsight(
                    insight_id=_insight_uuid(InsightCategory.UNSTABLE_STEP, sid),
                    category=InsightCategory.UNSTABLE_STEP,
                    severity=_severity_for_count(len(exec_set)),
                    title=f"unstable_step:{sid[:48]}",
                    description=(
                        f"Step id '{sid}' appears in patterns across {len(exec_set)} execution(s) "
                        f"(threshold {UNSTABLE_STEP_MIN_EXECUTIONS})."
                    ),
                    evidence_count=len(exec_set),
                    affected_workflows=wfs,
                    affected_steps=[sid],
                    suggested_action="Inspect step executor, tools, and validation for this step id.",
                    related_execution_ids=list(exec_set)[:200],
                    rank_score=len(exec_set) * 7,
                    evidence={"step_id": sid, "distinct_executions": len(exec_set)},
                )
            )

        return out[:UNSTABLE_LIMIT]

    def _ranked_suggestions(
        self,
        feedback: list[ExecutionFeedback],
        wf_by_exec: dict,
    ) -> list[RankedImprovementSuggestion]:
        bucket: dict[tuple[str, str], list] = defaultdict(list)
        wf_bucket: dict[tuple[str, str], set[str]] = defaultdict(set)

        for fb in feedback:
            for sug in fb.improvement_suggestions:
                key = (sug.category, sug.summary)
                bucket[key].append(fb.execution_id)
                wf = wf_by_exec.get(fb.execution_id)
                if wf:
                    wf_bucket[key].add(wf)

        ranked_keys = sorted(
            bucket.keys(),
            key=lambda k: (-len(bucket[k]), k[0], k[1]),
        )[:RANKED_SUGGESTIONS_LIMIT]

        out: list[RankedImprovementSuggestion] = []
        for rank, (cat, summary) in enumerate(ranked_keys, start=1):
            execs = list(dict.fromkeys(bucket[(cat, summary)]))
            count = len(execs)
            action = (
                "Review policy pack and workflow alignment."
                if cat == "policy_rule"
                else f"Address advisory category '{cat}' via governed release."
            )
            out.append(
                RankedImprovementSuggestion(
                    rank=rank,
                    category=cat,
                    summary=summary,
                    evidence_count=count,
                    affected_workflows=sorted(wf_bucket[(cat, summary)])[:32],
                    related_execution_ids=execs[:200],
                    suggested_action=action,
                    detail={"aggregation": "identical category+summary across execution_feedback rows"},
                )
            )
        return out
