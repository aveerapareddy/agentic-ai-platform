# platform-observability

Lightweight **operational** observability for the platform: structured events and an in-memory metrics registry with Prometheus text export.

This package does **not** compute business metrics (see `evaluation-engine` for trace-grounded evaluation). It records operational counters/timers only.

## Components

- **`observability.events`** — JSON-friendly structured log lines (no raw prompts).
- **`observability.metrics`** — thread-safe counters and latency totals; `render_prometheus()`.
- **`observability.tracing`** — optional span context managers (OpenTelemetry-lite, no OTel SDK).

## Usage

```python
from observability import get_registry, emit_event, observe_latency_ms

registry = get_registry()
observe_latency_ms("model_request", 120, labels={"provider": "fake"})
registry.inc("model_failures_total", labels={"reason": "timeout"})
emit_event("model_request", execution_id="…", step_id="…", latency_ms=120)
```

## Limitations

- In-process registry only (not distributed).
- No log shipping or dashboards bundled.
- Business evaluation metrics remain in `evaluation-engine`.
