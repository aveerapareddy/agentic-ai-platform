"""Deterministic scalar score from aggregated means (documented, not model-based)."""

from __future__ import annotations

from evaluation_engine.models import AggregatedMetrics, ExecutionMetrics


def compute_evaluation_score(
    aggregated: AggregatedMetrics,
    per_execution: list[ExecutionMetrics],
) -> tuple[float | None, str | None]:
    """
    Blend mean tool success and inverse mean fallback where available.

    When both signals exist:
      score = 0.45 * mean(tool_success_rate) + 0.45 * (1 - mean(model_fallback_rate))
              + 0.10 * (1 - failed/total)

    When only one signal exists, that signal receives the combined 0.90 weight for the
    quality components (documented renormalization).
    """
    _ = aggregated
    if not per_execution:
        return None, None

    tr = [m.tool_success_rate for m in per_execution if m.tool_success_rate is not None]
    fb = [m.model_fallback_rate for m in per_execution if m.model_fallback_rate is not None]

    tool_part = sum(tr) / len(tr) if tr else None
    fb_part = 1.0 - (sum(fb) / len(fb)) if fb else None

    n = len(per_execution)
    failed = sum(1 for m in per_execution if m.execution_status == "failed")
    fail_penalty = failed / n if n else 0.0
    base = 0.10 * (1.0 - fail_penalty)

    if tool_part is not None and fb_part is not None:
        score = 0.45 * tool_part + 0.45 * fb_part + base
        notes = (
            "0.45*mean(tool_success) + 0.45*(1-mean(model_fallback_rate)) + 0.10*(1-failed/total)"
        )
    elif tool_part is not None:
        score = 0.90 * tool_part + base
        notes = "tool signal only: 0.90*mean(tool_success) + 0.10*(1-failed/total)"
    elif fb_part is not None:
        score = 0.90 * fb_part + base
        notes = "fallback signal only: 0.90*(1-mean(model_fallback_rate)) + 0.10*(1-failed/total)"
    else:
        return None, "No tool_success_rate or model_fallback_rate on any execution in scope."

    return round(score, 4), notes
