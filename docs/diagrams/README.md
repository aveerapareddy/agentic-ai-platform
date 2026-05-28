# Architecture diagrams

Engineering diagrams for portfolio, README, and walkthroughs. **Draw.io** sources (`.drawio`) are editable in [diagrams.net](https://app.diagrams.net/); **SVG** exports match the same topology.

| File | Topic |
|------|--------|
| [system-overview.drawio](system-overview.drawio) / [.svg](system-overview.svg) | Services, trust boundaries, operator-console → gateway only |
| [execution-lifecycle.drawio](execution-lifecycle.drawio) / [.svg](execution-lifecycle.svg) | Execution states, validation gate, replay lineage |
| [replay-architecture.drawio](replay-architecture.drawio) / [.svg](replay-architecture.svg) | Source, replay child, provenance, diff |
| [mukti-analysis-flow.drawio](mukti-analysis-flow.drawio) / [.svg](mukti-analysis-flow.svg) | Traces → feedback → advisory insights |
| [streaming-architecture.drawio](streaming-architecture.drawio) / [.svg](streaming-architecture.svg) | Repository poll → gateway SSE → console |
| [cost-attribution-workflow.drawio](cost-attribution-workflow.drawio) / [.svg](cost-attribution-workflow.svg) | Cost workflow steps and services |

Diagrams reflect the **current** in-process local stack (gateway bundles runtime services) and **logical** service boundaries in code.
