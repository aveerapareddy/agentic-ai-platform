# Tradeoffs

One-line purpose: explicit engineering tradeoffs and rationale—aligned with constitution and current code.

## Deterministic control plane vs AI flexibility

**Choice:** Execution lifecycle, scheduling, and validation gates are **deterministic** and code-owned; models supply **bounded, schema-validated** payloads inside selected steps only.

**Rationale:** Constitution §2.3 and §8.4 require predictable audit and replay; unconstrained model-driven state transitions would violate platform identity.

**Cost:** Less “magic” from open-ended LLM planning; new step shapes require schema and orchestration work.

## Custom orchestration vs framework-centric stacks

**Choice:** No LangChain/LangGraph (or similar) as the **core** execution engine (constitution §8.3).

**Rationale:** Frameworks optimize for different goals; this platform prioritizes **explicit graphs**, **first-class policy rows**, and **service boundaries** over lowest time-to-demo.

**Cost:** More bespoke code for scheduling and integration; team owns the state machine.

## Bounded services vs monolithic convenience

**Choice:** Separate deployable modules (orchestrator, policy-engine, tool-runtime, knowledge-service, model-runtime, feedback-service, mukti-agent) with **common-schemas** contracts.

**Rationale:** Independent scaling, security review, and ownership per **system-overview.md**; audit clarity (“who decided” vs “who acted”).

**Cost:** Cross-service refactors and local dev need multiple paths on `PYTHONPATH` or packaging; no single binary convenience.

## Rule-based Mukti vs ML-first Mukti

**Choice:** Phase 6 ships **deterministic** pattern and failure classification from trace and governance inputs.

**Rationale:** Reproducible tests, no training data dependency, strict non-control-plane guarantee easier to reason about.

**Cost:** Weaker discovery of novel failure clusters; future ML layers would sit **behind** the same `ExecutionFeedback` contract.

## Latency vs completeness

**Choice:** Synchronous policy, tool, retrieval, and model calls on the hot path; validation mandatory before success.

**Rationale:** Simpler failure semantics and operator mental model for the current scale target.

**Cost:** Tail latency stacks per step; production may later add async tools **inside** tool-runtime without changing orchestrator contracts (per runtime model).

## Centralized policy evaluation

**Choice:** policy-engine is the locus of allow/deny/conditional logic; orchestrator forwards requests.

**Rationale:** Constitution §3.1—policy independent of agent prompts.

**Cost:** Network hop and availability coupling; mitigated by treating policy failure as a **gated** error with explicit handling (see system-overview failure isolation).

## Open items

- **api-gateway** authz model and trace redaction policies at HTTP boundary.
- **Object storage** for large artifacts if step outputs exceed JSONB comfort.
- **Queue-based** Mukti fan-out vs direct invoke.
