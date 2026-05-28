from observability.metrics import MetricsRegistry, render_prometheus


def test_counters_and_prometheus_render() -> None:
    reg = MetricsRegistry()
    reg.inc("model_failures_total", labels={"reason": "timeout"})
    reg.observe_latency_ms("model_request_ms", 42.0, labels={"provider": "fake"})
    text = render_prometheus(reg)
    assert "model_failures_total" in text
    assert 'reason="timeout"' in text
    assert "model_request_ms_sum" in text
