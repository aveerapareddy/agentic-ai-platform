# Product summary

One-line purpose: one-page internal summary of what exists, what it is for, and how mature it is.

## Audience

Platform engineers, backend owners, and technical program stakeholders who need a single reference without reading the full constitution or runtime model.

## Overview

The Agentic AI Platform is a **governed execution substrate**: work is modeled as **executions** with versioned **plans**, **steps**, persisted **results**, and a **trace** sufficient to audit policy, tools, validation, and optional model assistance. It is designed for internal operators extending workflows—not as a customer-facing chat product.

## Why this platform exists

Enterprises need automation that remains **inspectable** and **controllable** when models and agents are involved. The platform encodes separation between **lifecycle and policy** (deterministic, data-backed) and **reasoning or retrieval** (bounded inside steps, schema-validated at boundaries). That split supports incident-style operations, cost governance scenarios, and any workflow requiring approval gates before side effects.

## Capabilities (as implemented)

- **Execution lifecycle** with explicit states and validation-before-success semantics.
- **Incident triage** workflow: analyze (model-runtime with deterministic fallback), gather evidence (tool-runtime + knowledge-service), validate (model-runtime with fallback), terminal result with governance on escalation proposals.
- **Policy-engine**: synchronous allow / deny / conditional evaluation with persisted evaluations.
- **Action proposals, approvals**: persisted; `awaiting_approval` path for conditional policy.
- **Tool-runtime**: read-only registered tools with durable **tool_calls** rows.
- **Knowledge-service**: deterministic local corpus retrieval into step evidence.
- **Model-runtime**: structured `StructuredReasoningClient`; default fake provider (no live LLM required).
- **Feedback-service**: operator feedback rows; Mukti **execution_feedback** rows.
- **Mukti-agent**: rule-based post-execution classifier producing structured failure types, patterns, and improvement suggestions (advisory only).
- **PostgreSQL schema** and **in-memory** repositories for development and tests.

## Workflows

- **Incident triage**: primary, end-to-end demonstration workflow.
- **Generic / cost_attribution placeholder**: planner emits a two-step reasoning→validation plan; no cost-specific retrieval or tools yet—treated as a **template** for future vertical work.

## Current maturity

Aligned with **Phase 6** delivery in `project-end-state.md`: core execution, governance, tools, knowledge, bounded AI, feedback, and deterministic Mukti are **implemented in code**. **api-gateway** and **operator-console** are **not** implemented. **Cost attribution** as a full vertical is **not** implemented. Multi-workflow “complete” criteria in the end-state (e.g. two major workflows fully demonstrated) remain **aspirational** relative to the current tree.

## Relationship to enterprise systems

The codebase assumes integrations (ticketing, cloud control planes, identity) will be reached **through registered tools** and **execution context** (tenant, environment, policy scope)—not by embedding vendor SDKs in the orchestrator. Today, tools and retrieval are **local/deterministic** stand-ins.

## Non-consumer positioning

This is **infrastructure**: operators and engineers extend services and contracts. It is not positioned as a self-serve consumer application; any future gateway or console would sit on top of the same execution and trace contracts.

## Success criteria (for this repository phase)

- Service boundaries in code match **constitution §8.2** (orchestrator does not own policy rules, tool bodies, retrieval indexes, or Mukti logic).
- **Incident triage** runs end-to-end with trace and persistence patterns that survive review against `runtime-model.md`.
- **No silent paths**: failures and governance outcomes are recorded in trace or normalized storage.
- **Mukti and operator feedback** never mutate in-flight execution rows.
