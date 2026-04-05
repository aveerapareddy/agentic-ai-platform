# Problem statement

One-line purpose: articulate the operational and engineering problems this platform addresses.

## Context

Teams automate operational work across ticketing, observability, cost, and control-plane APIs. Large language models can draft summaries or suggestions, but **production control** requires stable identifiers, repeatable structure, and explicit gates for anything that changes external state or carries compliance risk.

## Problem

Without a shared execution layer:

- **Behavior lives in prompts and notebooks**, making audit (“who approved what”) and replay difficult.
- **Side effects** risk being triggered directly from model output without consistent policy or registration.
- **Failure modes** are hard to classify; partial success is often indistinguishable from clean success in logs alone.
- **Improvement loops** conflate live behavior with retrospective analysis, encouraging unsafe self-modification.

## Why existing approaches fail

- **Chat-first or framework-first stacks** optimize for conversational UX or rapid demos, not durable execution graphs, stored validation outcomes, or first-class policy records.
- **Ad hoc RAG** centers retrieval as the product; it does not substitute for step-scoped evidence, tool contracts, and governance on mutations.
- **Monolithic “agent” services** collapse planning, policy, and tool execution, weakening separation of duties and audit.

## Platform objective

Provide a **small set of services** and **shared schemas** such that:

1. Every meaningful run is an **execution** with a **plan**, **steps**, and a **trace** aligned with `runtime-model.md`.
2. **Policy** and **tools** are invoked through dedicated components; orchestration coordinates but does not own those rules or implementations.
3. **Validation** is a recorded gate before terminal success.
4. **Post-execution analysis** (Mukti) produces **structured, advisory** feedback without changing live run state.

## Success criteria

- Operators can answer: what ran, in what order, what policy said, what tools ran, what was validated, and what failed—**from stored data**, not only from unstructured logs.
- Extensions (new tools, policy packs, workflows) ship through **code and configuration**, not runtime mutation from analysis output.
- The design remains **credible as an internal platform** under code review against `project-constitution.md`.

## Constraints

Bounded by **project-constitution.md** and **project-end-state.md**: no framework-centric orchestration engine; no Mukti control of the orchestrator; contracts from `common-schemas`; relational system of record for execution graph per constitution §5.2.
