# model-runtime (Phase 5)

Bounded **structured** inference for incident triage reasoning steps. Providers return Pydantic models from `common_schemas.reasoning`; no prompt-to-state shortcuts.

- **`FakeStructuredProvider`**: deterministic, no network (default).
- **`UnconfiguredHttpProvider`**: stub for a future real HTTP-backed client; raises if invoked.

**API:** `ModelRuntimeService.analyze_incident` / `validate_incident`.

The orchestrator records trace events for `model_runtime` vs `deterministic_fallback` paths.
