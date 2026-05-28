# Demo screenshots

Static captures of **operator-console** views for README, portfolio, and walkthroughs.

## Source

Screenshots are generated from **screenshot fixtures** (`docs/assets/screenshot-fixtures/`) that use the same dark theme tokens as [ui-system.md](../../design/ui-system.md) and **deterministic demo IDs** aligned with [docs/examples/](../examples/).

Regenerate after UI changes:

```bash
pip install playwright
playwright install chromium
python scripts/capture_demo_screenshots.py
```

Requires only fixtures (no running stack). For **live** captures against Docker console, set `CAPTURE_LIVE=1` and `CONSOLE_URL=http://localhost:4200` (see script).

## Index

| File | View |
|------|------|
| `01-execution-explorer.png` | Execution list |
| `02-execution-detail.png` | Execution detail summary |
| `03-trace-timeline.png` | Trace timeline (grouped steps) |
| `04-replay-comparison.png` | Replay diff |
| `05-metrics-evaluation.png` | Platform metrics |
| `06-mukti-insights.png` | Mukti insights |
| `07-policy-simulation.png` | Policy simulate (admin) |
| `08-streaming-execution.png` | Live SSE indicator on detail |
| `09-cost-attribution-workflow.png` | Cost attribution execution |
| `10-incident-triage-workflow.png` | Incident triage execution |
