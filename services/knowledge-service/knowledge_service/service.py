"""Retrieval API: scoped query → structured chunks."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from common_schemas import RetrievalId, RetrievalRequest, RetrievalResponse

from knowledge_service.retrieval import DEFAULT_CORPUS, retrieve_from_corpus


class KnowledgeService:
    """Owns retrieval behavior; orchestrator calls `retrieve` only (constitution §8.2)."""

    def __init__(self, corpus: list[dict[str, Any]] | None = None) -> None:
        self._corpus: list[dict[str, Any]] = [dict(d) for d in (corpus or DEFAULT_CORPUS)]

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        chunks = retrieve_from_corpus(request, self._corpus)
        rid: RetrievalId = uuid4()
        return RetrievalResponse(
            retrieval_id=rid,
            query=request.query,
            chunks=chunks,
            corpus_version="phase4_local_v1",
            metadata={
                "tenant_id": request.tenant_id,
                "workflow_type": request.workflow_type,
                "filters": dict(request.filters),
            },
        )
