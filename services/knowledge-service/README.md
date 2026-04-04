# knowledge-service (Phase 4)

Deterministic retrieval from a small in-memory corpus. Returns `RetrievalResponse` with `EvidenceChunk` entries suitable for `StepResult.evidence`.

**API:** `KnowledgeService.retrieve(RetrievalRequest) -> RetrievalResponse`.

Tenant and workflow type are carried for scoping metadata; matching is keyword overlap against corpus `keywords` (Phase 4 stub).
