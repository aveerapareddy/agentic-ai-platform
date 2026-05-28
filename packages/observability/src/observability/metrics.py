"""In-memory counters and latency totals with Prometheus text export."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

_global: MetricsRegistry | None = None
_lock = threading.Lock()


def get_registry() -> MetricsRegistry:
    global _global
    with _lock:
        if _global is None:
            _global = MetricsRegistry()
        return _global


def _label_key(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
    if not labels:
        return ()
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


class MetricsRegistry:
    """Thread-safe operational metrics (not evaluation/business metrics)."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._latency_sum: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._latency_count: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._mutex = threading.Lock()

    def inc(self, name: str, value: float = 1.0, *, labels: dict[str, str] | None = None) -> None:
        key = (name, _label_key(labels))
        with self._mutex:
            self._counters[key] += value

    def observe_latency_ms(
        self,
        name: str,
        latency_ms: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        key = (name, _label_key(labels))
        with self._mutex:
            self._latency_sum[key] += latency_ms
            self._latency_count[key] += 1.0

    def snapshot(self) -> dict[str, Any]:
        with self._mutex:
            return {
                "counters": dict(self._counters),
                "latency_sum": dict(self._latency_sum),
                "latency_count": dict(self._latency_count),
            }

    def reset(self) -> None:
        with self._mutex:
            self._counters.clear()
            self._latency_sum.clear()
            self._latency_count.clear()


def observe_latency_ms(
    metric_base: str,
    latency_ms: float,
    *,
    labels: dict[str, str] | None = None,
) -> None:
    reg = get_registry()
    reg.observe_latency_ms(f"{metric_base}_ms", latency_ms, labels=labels)
    reg.inc(f"{metric_base}_count", labels=labels)


def render_prometheus(registry: MetricsRegistry | None = None) -> str:
    reg = registry or get_registry()
    lines: list[str] = []
    snap = reg.snapshot()
    counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = snap["counters"]
    for (name, label_tuples), value in sorted(counters.items()):
        label_str = _prom_labels(label_tuples)
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name}{label_str} {value}")
    latency_sum: dict[tuple[str, tuple[tuple[str, str], ...]], float] = snap["latency_sum"]
    latency_count: dict[tuple[str, tuple[tuple[str, str], ...]], float] = snap["latency_count"]
    for key, total in sorted(latency_sum.items()):
        name, label_tuples = key
        count = latency_count.get(key, 0.0)
        label_str = _prom_labels(label_tuples)
        sum_name = name if name.endswith("_ms") else f"{name}_ms"
        lines.append(f"# TYPE {sum_name} summary")
        lines.append(f"{sum_name}_sum{label_str} {total}")
        lines.append(f"{sum_name}_count{label_str} {count}")
    return "\n".join(lines) + ("\n" if lines else "")


def _prom_labels(label_tuples: tuple[tuple[str, str], ...]) -> str:
    if not label_tuples:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in label_tuples)
    return "{" + inner + "}"
