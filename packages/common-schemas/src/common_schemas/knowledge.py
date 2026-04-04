"""Knowledge retrieval contracts (orchestrator → knowledge-service boundary)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .ids import RetrievalId


class RetrievalRequest(BaseModel):
    """Scoped retrieval query; knowledge-service owns matching semantics."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    workflow_type: str
    query: str
    max_results: int = Field(default=5, ge=1, le=50)
    filters: dict[str, Any] = Field(default_factory=dict)
    correlation_request_id: str | None = Field(
        default=None,
        description="Optional execution_context.request_id for audit correlation.",
    )


class EvidenceChunk(BaseModel):
    """Citable unit suitable for StepResult.evidence."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    source_uri: str
    title: str | None = None
    text_excerpt: str
    score: float | None = Field(default=None, ge=0.0, le=1.0)


class RetrievalResponse(BaseModel):
    """Structured retrieval outcome for evidence attachment."""

    model_config = ConfigDict(extra="forbid")

    retrieval_id: RetrievalId
    query: str
    chunks: list[EvidenceChunk] = Field(default_factory=list)
    corpus_version: str = Field(
        default="phase4_local_v1",
        description="Corpus snapshot label for replay and audit.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
