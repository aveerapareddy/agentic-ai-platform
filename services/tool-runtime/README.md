# tool-runtime

Registered, policy-aware **tool execution** for the platform. Tools return structured dict outputs; orchestrator persists `ToolCall` rows and trace events.

## Tools (default registry)

| Tool | Side effect | Notes |
|------|-------------|--------|
| `incident_system_tool` | read_only | Incident metadata (simulated latency/errors) |
| `incident_system_update_tool` | state_changing | Requires `approved=true`; local status store |
| `metrics_lookup_tool` | read_only | Synthetic metrics/log snapshots |
| `cloud_cost_tool` | read_only | Cost attribution snapshot |
| `incident_metadata_tool` | read_only | Alias for orchestrator compatibility |
| `signal_lookup_tool` | read_only | Alias for metrics lookup |

## Runtime behavior

- **Retries:** transient failures only (`ConnectionError`, `TimeoutError`, etc.) per `ToolRetryPolicy`
- **Timeouts:** `timeout_bounds_ms` enforced via bounded thread pool wait
- **Cancellation:** optional `cancel_check` on `ToolRuntimeService` / `with_cancel_check()`
- **Policy:** `ToolInvokeRequest.policy_denied=True` → `REJECTED_BY_POLICY` without invoking handler
- **Observability:** structured `tool_invoke` / `tool_completed` events and counters (Session B package)

## Limitations

- Local fixtures and in-memory mutating state (not multi-process safe)
- No distributed tool worker pool
- Orchestrator owns when tools are invoked and policy gates for mutating tools
