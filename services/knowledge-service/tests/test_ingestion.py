"""Ingestion and chunking behavior."""

from __future__ import annotations

from knowledge_service.ingestion import chunk_text, ingest_document
from knowledge_service.service import KnowledgeService


def test_chunk_text_deterministic_overlap() -> None:
    text = "word " * 120
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1
    assert all(len(c) <= 50 for c in chunks)


def test_ingest_document_assigns_ids_and_metadata() -> None:
    rows = ingest_document(
        document_id="doc-1",
        source_uri="kb://custom/doc-1",
        title="Custom",
        text="cost billing anomaly spend attribution",
        metadata={"team": "finops", "document_type": "playbook"},
        corpus_version="test_v1",
    )
    assert rows
    assert rows[0]["document_id"] == "doc-1"
    assert rows[0]["corpus_version"] == "test_v1"
    assert rows[0]["metadata"]["team"] == "finops"


def test_service_ingest_then_retrieve() -> None:
    svc = KnowledgeService(corpus_version="test_v2")
    svc.ingest_document(
        document_id="doc-ingest",
        source_uri="kb://ingest/doc",
        title="Ingested cost note",
        text="billing spend spike cost attribution finops",
        metadata={"team": "finops", "workflow": "cost_attribution"},
    )
    from common_schemas import RetrievalRequest

    r = svc.retrieve(
        RetrievalRequest(
            tenant_id="t",
            workflow_type="cost_attribution",
            query="billing spend cost attribution",
            filters={"team": "finops"},
            max_results=5,
        ),
    )
    assert r.chunks
    assert any(c.document_id == "doc-ingest" for c in r.chunks)
    assert r.metadata.get("latency_ms") is not None
