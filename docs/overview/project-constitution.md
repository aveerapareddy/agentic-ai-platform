# Project Constitution

One-line purpose: Non-negotiable engineering principles governing design, implementation, and evolution of the Agentic AI Platform.

This document defines how the system must be built.  
If implementation conflicts with this document, the implementation is incorrect.

---

## 1. System Identity

The system is:

- a multi-agent execution platform  
- a control plane for workflows involving models, tools, and data  
- a system with explicit execution semantics and traceability  

The system is not:

- a chatbot  
- a prompt wrapper  
- a collection of loosely connected scripts  
- a framework-driven demo  

---

## 2. Execution and Agents

### 2.1 Explicit Execution Model
- All workflows must be represented as structured execution plans
- Execution must be step-based and stateful
- No critical behavior may exist only in prompts

### 2.2 Bounded Agents
- Agents must have clearly defined responsibilities
- Agents must operate through structured inputs and outputs
- No “general-purpose” or “god” agent is allowed

### 2.3 Deterministic Control Layer
- Execution lifecycle, retries, and state transitions must be deterministic
- AI components must not control system state directly

---

## 3. Policy and Safety

### 3.1 Separation of Policy
- Policy evaluation must be independent from agent logic
- Agents may propose actions, but cannot execute them directly

### 3.2 Controlled Side Effects
- All state-changing operations must go through:
  - tool runtime
  - policy evaluation
  - approval (if required)

### 3.3 Approval as First-Class
- High-risk actions must support human approval
- Approval decisions must be recorded and auditable

---

## 4. Observability and Reliability

### 4.1 Full Traceability
- Every execution must record:
  - steps
  - tool calls
  - decisions
  - validation outcomes
- No silent execution paths are allowed

### 4.2 Failure is Expected
- Failures must be classified (tool, validation, policy, timeout, etc.)
- Failures must be recorded explicitly
- The system must never silently degrade without trace

### 4.3 Replayability
- Executions must be replayable
- Replay must preserve execution structure and inputs
- Debugging must not depend on external system availability

---

## 5. Data, Retrieval, and Traceability

### 5.1 Contracts Over Ad-hoc Data
- All services must use shared schemas from `packages/common-schemas`
- No loosely typed or implicit data exchange

### 5.2 Storage by Responsibility
- Execution state must be stored in relational storage
- Artifacts and large outputs may be stored externally
- Retrieval data must be clearly separated from execution state

### 5.3 Trace Completeness
- Trace data must be sufficient to reconstruct decisions
- Missing data must be explicitly marked, not hidden

---

## 6. Evaluation and Improvement

### 6.1 Validation Before Completion
- No execution may be marked complete without validation
- Validation must be explicit and recorded

### 6.2 Mukti (Execution Feedback)
- Mukti operates post-execution only
- It analyzes traces to detect patterns and failures
- It produces advisory improvements only

### 6.3 Controlled Evolution
- System behavior must not change automatically at runtime
- Improvements must be introduced through controlled updates

---

## 7. Documentation and Change Control

### 7.1 Docs-First Development
- Architecture and contracts must be defined before implementation
- Code must reflect documented behavior

### 7.2 No Implicit Behavior
- If behavior is not documented, it is considered undefined
- Hidden logic is not allowed

### 7.3 Backward Compatibility
- Contracts must evolve carefully
- Breaking changes must be explicit and justified

---

## 8. Implementation and Development Rules

### 8.1 Contracts First
- All code must use shared schemas
- No ad-hoc request/response shapes

### 8.2 Separation of Concerns (Strict)
- Orchestrator must not implement:
  - policy logic
  - tool execution
  - retrieval
- Each service owns its responsibility

### 8.3 No Framework-Centric Design
- The platform must not depend on LangChain, LangGraph, or similar frameworks as the core execution engine
- Frameworks may be used internally, but must not define system behavior

### 8.4 Deterministic Core
- Core execution must remain predictable and auditable
- Non-determinism must be isolated to controlled components

### 8.5 No Shortcuts
- No bypassing validation, policy, or trace recording
- No temporary hacks that violate architecture

### 8.6 Minimal but Correct
- Initial implementations must be simple but structurally correct
- Do not add features outside the defined scope

### 8.7 Code Quality Expectations
- Strong typing
- Clear naming
- Small, testable units
- No dead code
- No ambiguous abstractions

---

## 9. Decision Rule

For any design or implementation decision:

> Does this make the system more like a production-grade internal platform, or more like a demo?

If it reduces clarity, control, or reliability, it must be rejected or redesigned.

---

## 10. Evolution Strategy

- Build foundation first (execution, state, contracts)
- Add capabilities incrementally (policy, tools, AI)
- Preserve architectural integrity across phases

---

## 11. Implementation Enforcement Rules

### 11.1 Mandatory Reference Documents

Before implementing any code or generating any design:

- docs/overview/project-constitution.md
- docs/overview/project-end-state.md

These documents define non-negotiable system constraints.

---

### 11.2 Deviation Detection Requirement

If a requested implementation:

- violates service boundaries
- introduces hidden logic
- bypasses shared schemas
- collapses separation of concerns
- contradicts execution semantics
- introduces framework-driven control flow
- deviates from defined phase outputs

The implementation MUST NOT proceed silently.

Instead, the system must:

1. Explicitly identify the violation
2. Explain why it conflicts with the constitution or end-state
3. Propose a compliant alternative

---

### 11.3 No Silent Simplification

The system must not:

- simplify architecture to make code easier
- remove layers defined in architecture
- merge services for convenience
- skip validation, policy, or trace requirements

If simplification is necessary, it must be:

- explicitly justified
- aligned with the end-state
- approved as an intentional design decision

---

### 11.4 Phase Alignment Enforcement

Every implementation must align with a defined phase from project-end-state.md.

The system must:

- identify the current phase
- ensure only scope relevant to that phase is implemented
- prevent premature implementation of future-phase features

---

### 11.5 Contract Integrity

All inter-component communication must:

- use shared schemas from packages/common-schemas
- avoid ad-hoc structures
- preserve backward compatibility unless explicitly changed

---

### 11.6 Architecture as Source of Truth

If there is a conflict between:

- implementation convenience
- or architecture definition

Architecture must be treated as correct.

---

### 11.7 Explicit Justification for Changes

Any deviation from:

- runtime-model.md
- system-overview.md
- api-design.md

Must include:

- reason for deviation
- impact analysis
- why it improves the system