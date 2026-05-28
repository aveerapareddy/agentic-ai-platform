"""Retrieval API: scoped query → structured chunks with ingestion support."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from common_schemas import RetrievalId, RetrievalRequest, RetrievalResponse

from knowledge_service.ingestion import ingest_document
from knowledge_service.retrieval import DEFAULT_CORPUS, retrieve_from_corpus

DEFAULT_CORPUS_VERSION = "phase5_local_v1"

try:
    from observability import emit_event, get_registry, observe_latency_ms
except ImportError:  # pragma: no cover

    def emit_event(_event_type: str, **_fields: Any) -> None:
        return None

    def observe_latency_ms(*_a: Any, **_k: Any) -> None:
        return None

    def get_registry() -> Any:
        class _Noop:
            def inc(self, *_a: Any, **_k: Any) -> None:
                return None

        return _Noop()


class KnowledgeService:
    """Owns retrieval behavior; orchestrator calls `retrieve` only (constitution §8.2)."""

    def __init__(
        self,
        corpus: list[dict[str, Any]] | None = None,
        *,
        corpus_version: str = DEFAULT_CORPUS_VERSION,
    ) -> None:
        self._corpus_version = corpus_version
        self._corpus: list[dict[str, Any]] = [dict(d) for d in (corpus or DEFAULT_CORPUS)]

    @property
    def corpus_version(self) -> str:
        return self._corpus_version

    def ingest_document(
        self,
        *,
        document_id: str,
        source_uri: str,
        title: str,
        text: str,
        metadata: dict[str, Any] | None = None,
        corpus_version: str | None = None,
    ) -> list[dict[str, Any]]:
        version = corpus_version or self._corpus_version
        rows = ingest_document(
            document_id=document_id,
            source_uri=source_uri,
            title=title,
            text=text,
            metadata=metadata,
            corpus_version=version,
        )
        self._corpus.extend(rows)
        return rows

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        started = time.perf_counter()
        chunks, version = retrieve_from_corpus(request, self._corpus)
        latency_ms = int((time.perf_counter() - started) * 1000)
        rid: RetrievalId = uuid4()
        corpus_label = request.corpus_version or version
        observe_latency_ms(
            "knowledge_retrieval",
            float(latency_ms),
            labels={"workflow_type": request.workflow_type},
        )
        get_registry().inc(
            "knowledge_retrievals_total",
            labels={"workflow_type": request.workflow_type},
        )
        emit_event(
            "knowledge_retrieval",
            retrieval_id=str(rid),
            tenant_id=request.tenant_id,
            workflow_type=request.workflow_type,
            chunk_count=len(chunks),
            corpus_version=corpus_label,
            latency_ms=latency_ms,
        )
        return RetrievalResponse(
            retrieval_id=rid,
            query=request.query,
            chunks=chunks,
            corpus_version=corpus_label,
            metadata={
                "tenant_id": request.tenant_id,
                "workflow_type": request.workflow_type,
                "filters": dict(request.filters),
                "latency_ms": latency_ms,
                "corpus_version_requested": request.corpus_version,
            },
        )
