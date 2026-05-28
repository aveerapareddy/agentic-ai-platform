"""Retrieval response shape and deterministic matching."""

from __future__ import annotations

from common_schemas import EvidenceChunk, RetrievalRequest
from knowledge_service.service import KnowledgeService


def test_retrieval_returns_chunks_and_ids() -> None:
    svc = KnowledgeService()
    r = svc.retrieve(
        RetrievalRequest(
            tenant_id="t",
            workflow_type="incident_triage",
            query="latency error spike deploy incident",
            max_results=3,
        ),
    )
    assert r.retrieval_id
    assert r.corpus_version
    assert r.chunks
    for ch in r.chunks:
        assert isinstance(ch, EvidenceChunk)
        assert ch.chunk_id
        assert ch.source_uri.startswith("kb://")
        assert ch.text_excerpt


def test_retrieval_metadata_includes_tenant_workflow() -> None:
    svc = KnowledgeService()
    r = svc.retrieve(
        RetrievalRequest(
            tenant_id="acme",
            workflow_type="incident_triage",
            query="config drift",
        ),
    )
    assert r.metadata.get("tenant_id") == "acme"
    assert r.metadata.get("workflow_type") == "incident_triage"


def test_evidence_chunk_includes_document_and_metadata() -> None:
    svc = KnowledgeService()
    r = svc.retrieve(
        RetrievalRequest(
            tenant_id="t",
            workflow_type="cost_attribution",
            query="cost billing spend anomaly",
            max_results=2,
        ),
    )
    assert r.chunks
    ch = r.chunks[0]
    assert ch.document_id
    assert ch.score is not None
    assert isinstance(ch.metadata, dict)


def test_corpus_version_filter() -> None:
    svc = KnowledgeService(corpus_version="phase5_local_v1")
    r = svc.retrieve(
        RetrievalRequest(
            tenant_id="t",
            workflow_type="cost_attribution",
            query="optimization rightsizing cost",
            corpus_version="phase5_local_v1",
            max_results=3,
        ),
    )
    assert r.corpus_version == "phase5_local_v1"
