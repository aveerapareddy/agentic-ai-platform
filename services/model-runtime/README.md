# model-runtime

Bounded **structured** inference for incident triage reasoning steps. Providers return Pydantic models from `common_schemas.reasoning`; no raw completions cross the orchestrator boundary.

## Providers

| Type | Env | Description |
|------|-----|-------------|
| `fake` | `MODEL_PROVIDER=fake` (default) | Deterministic, no network |
| `openai` | `MODEL_PROVIDER=openai`, `OPENAI_API_KEY` | OpenAI-compatible chat completions + JSON object response |
| `azure_openai` | `MODEL_PROVIDER=azure_openai`, `AZURE_OPENAI_*` | Azure deployment URL + `api-key` header |

## Configuration

| Variable | Purpose |
|----------|---------|
| `MODEL_PROVIDER` | `fake` \| `openai` \| `azure_openai` |
| `MODEL_API_KEY` / `OPENAI_API_KEY` / `AZURE_OPENAI_API_KEY` | Credentials (never hardcoded) |
| `MODEL_BASE_URL` / `OPENAI_BASE_URL` / `AZURE_OPENAI_ENDPOINT` | API base |
| `MODEL_NAME` | Model or deployment name |
| `AZURE_OPENAI_DEPLOYMENT` | Azure deployment id |
| `MODEL_TIMEOUT_SECONDS` | Per-request timeout (default 30) |
| `MODEL_MAX_RETRIES` | Transient retries (default 2) |
| `MODEL_RETRY_BACKOFF_SECONDS` | Linear backoff multiplier (default 0.5) |

## Retries

`ResilientStructuredProvider` retries **transient** failures (timeout, rate limit, network, HTTP 5xx/429). It does **not** retry schema validation failures or invalid requests.

## Token accounting

`ModelInvocationTelemetry` on structured outputs and `model_reasoning` trace rows (`invocation` payload) records:

- `input_tokens`, `output_tokens`, `total_tokens`
- `latency_ms`, `retry_count`, `provider_type`, `model_name`

## Fallback

The **orchestrator** still owns lifecycle. On provider failure, timeout, or schema error it records `model_reasoning` with `path: deterministic_fallback` and runs `StepExecutor` — no control-plane mutation in model-runtime.

## API

`ModelRuntimeService.analyze_incident` / `validate_incident` return `ReasoningCallResult` (`output` + `telemetry`).

## Limitations

- No chat/completions exposed outside provider internals.
- No workflow orchestration or policy logic in this service.
- HTTP providers require network; use `fake` for CI.
