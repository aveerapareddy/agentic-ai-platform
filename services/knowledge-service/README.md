# knowledge-service (Phase 5 / Session D)

Deterministic ingestion, chunking, and retrieval from an in-memory corpus. Returns `RetrievalResponse` with rich `EvidenceChunk` entries suitable for `StepResult.evidence`.

**API:** `KnowledgeService.retrieve(RetrievalRequest) -> RetrievalResponse`, `KnowledgeService.ingest_document(...)`.

## Ingestion and chunking

- `ingestion.ingest_document` splits text with fixed-size overlapping windows (deterministic).
- Each chunk gets `chunk_id`, `document_id`, `source_uri`, `keywords`, `metadata`, and `corpus_version`.
- `KnowledgeService.ingest_document` appends chunks to the active corpus.

## Retrieval

- Keyword overlap + lightweight semantic score (term-frequency cosine on title/body).
- **Metadata filters** (e.g. `team`, `service`, `workflow`, `document_type`) must match chunk metadata.
- Optional `RetrievalRequest.corpus_version` scopes to a snapshot label.
- Observability: `knowledge_retrieval` events, `knowledge_retrievals_total`, latency histogram.

## Evidence model

Each `EvidenceChunk` includes: `chunk_id`, `document_id`, `source_uri`, `title`, `text_excerpt`, `score`, `corpus_version`, `metadata`.

## Limitations

- Process-local storage only; restart clears ingested documents unless corpus is injected in tests.
- No vector database or cross-region replication.
- Default corpus is small (runbooks + cost playbooks).
