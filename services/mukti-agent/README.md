# mukti-agent (Phase 6)

Post-execution **MuktiAnalyzer** consumes `MuktiAnalysisInput` (execution, steps, results, trace, operator feedback, governance rows) and returns **`ExecutionFeedback`** (failure_types, patterns_detected, improvement_suggestions, advisory_confidence).

**No** orchestrator control APIs, **no** live execution mutation. Persist outputs with **feedback-service** `save_execution_feedback`.
