# feedback-service (Phase 6)

Ingests **operator_feedback** (human/integration labels) and persists **execution_feedback** (Mukti advisory rows). Separate tables and contracts; no orchestrator control-plane coupling.

**API:** `FeedbackService.submit_operator_feedback`, `save_execution_feedback`, list helpers.

**Repository:** `InMemoryFeedbackRepository` (tests), `PostgresFeedbackRepository` (shared DB with migrations `001` + `002`).
