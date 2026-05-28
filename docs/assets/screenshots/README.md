# Demo screenshots

Static captures of the **operator-console** for README, portfolio, and walkthroughs. Filenames are stable (`01-` … `10-`).

## Regenerate (preferred: live stack)

After `make docker-up` and `make docker-seed`:

```bash
pip install playwright
playwright install chromium
CAPTURE_LIVE=1 CONSOLE_URL=http://localhost:4200 make capture-screenshots
```

The script discovers demo execution IDs from **api-gateway** (`GATEWAY_URL`, default `http://127.0.0.1:8080`) and captures all ten views from the running Angular app.

## Offline fallback

```bash
make capture-screenshots
```

Uses HTML fixtures under `docs/assets/screenshot-fixtures/` (update fixtures when the console layout changes materially).

## Index

| File | Caption |
|------|---------|
| `01-execution-explorer.png` | Execution Explorer |
| `02-execution-detail.png` | Execution Detail |
| `03-trace-timeline.png` | Trace Timeline |
| `04-replay-comparison.png` | Replay Diff |
| `05-metrics-evaluation.png` | Metrics |
| `06-mukti-insights.png` | Mukti Insights |
| `07-policy-simulation.png` | Policy Simulation |
| `08-streaming-execution.png` | Live Activity |
| `09-cost-attribution-workflow.png` | Cost Attribution |
| `10-incident-triage-workflow.png` | Incident Triage |
