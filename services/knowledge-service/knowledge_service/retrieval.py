"""Deterministic matching over a small in-memory corpus."""

from __future__ import annotations

from typing import Any, TypedDict

from common_schemas import EvidenceChunk, RetrievalRequest


class _CorpusDoc(TypedDict):
    chunk_id: str
    source_uri: str
    title: str
    text_excerpt: str
    keywords: list[str]


DEFAULT_CORPUS: list[_CorpusDoc] = [
    {
        "chunk_id": "rb-slo-001",
        "source_uri": "kb://runbooks/slo-regression",
        "title": "SLO regression triage",
        "text_excerpt": (
            "When error rate and latency spike together, check recent deploys and dependency health. "
            "Correlate metrics window with change events."
        ),
        "keywords": ["latency", "error", "slo", "spike", "deploy", "incident"],
    },
    {
        "chunk_id": "rb-cap-002",
        "source_uri": "kb://runbooks/capacity",
        "title": "Capacity saturation",
        "text_excerpt": (
            "Saturation patterns include queue depth growth and timeout cascades. "
            "Validate autoscaling limits and downstream quotas."
        ),
        "keywords": ["capacity", "saturation", "queue", "timeout", "quota"],
    },
    {
        "chunk_id": "rb-config-003",
        "source_uri": "kb://runbooks/config-drift",
        "title": "Configuration drift",
        "text_excerpt": (
            "Config drift often follows partial rollouts. Compare effective config revision across instances."
        ),
        "keywords": ["config", "drift", "rollout", "incident"],
    },
]


def score_and_rank(query: str, corpus: list[_CorpusDoc], max_results: int) -> list[EvidenceChunk]:
    q = query.lower()
    tokens = {t for t in q.replace(",", " ").split() if len(t) > 1}
    scored: list[tuple[float, _CorpusDoc]] = []
    for doc in corpus:
        kws = {k.lower() for k in doc["keywords"]}
        overlap = len(tokens & kws)
        title_hit = doc["title"].lower() in q or any(t in doc["title"].lower() for t in tokens)
        score = float(overlap) + (0.5 if title_hit else 0.0)
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: (-x[0], x[1]["chunk_id"]))
    out: list[EvidenceChunk] = []
    for s, doc in scored[:max_results]:
        norm = min(1.0, s / 4.0)
        out.append(
            EvidenceChunk(
                chunk_id=doc["chunk_id"],
                source_uri=doc["source_uri"],
                title=doc["title"],
                text_excerpt=doc["text_excerpt"],
                score=round(norm, 3),
            ),
        )
    if not out and corpus:
        # Weak default: first doc with low score so retrieval is never empty for triage queries.
        doc = corpus[0]
        out.append(
            EvidenceChunk(
                chunk_id=doc["chunk_id"],
                source_uri=doc["source_uri"],
                title=doc["title"],
                text_excerpt=doc["text_excerpt"],
                score=0.1,
            ),
        )
    return out[:max_results]


def retrieve_from_corpus(
    request: RetrievalRequest,
    corpus: list[dict[str, Any]],
) -> list[EvidenceChunk]:
    normalized: list[_CorpusDoc] = []
    for raw in corpus:
        normalized.append(
            {
                "chunk_id": str(raw["chunk_id"]),
                "source_uri": str(raw["source_uri"]),
                "title": str(raw.get("title") or ""),
                "text_excerpt": str(raw["text_excerpt"]),
                "keywords": [str(k) for k in raw.get("keywords", [])],
            },
        )
    return score_and_rank(request.query, normalized, request.max_results)
