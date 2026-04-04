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
