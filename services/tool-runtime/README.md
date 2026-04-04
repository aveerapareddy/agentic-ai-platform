# tool-runtime (Phase 4)

Registered, deterministic tools only. The orchestrator sends `ToolInvokeRequest` and persists returned `ToolCall` rows; this service does not own execution lifecycle or policy.

**Tools (local):**

- `incident_metadata_tool` — read-only, idempotent; requires `incident_id` or `id` in input.
- `signal_lookup_tool` — read-only, idempotent; optional `signal_types` list.

**API:** `ToolRuntimeService.invoke(request, *, now=None) -> ToolCall`.
