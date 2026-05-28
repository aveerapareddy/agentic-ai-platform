"""Deterministic keyword + lightweight semantic matching over an in-memory corpus."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, TypedDict

from common_schemas import EvidenceChunk, RetrievalRequest


class _CorpusDoc(TypedDict, total=False):
    chunk_id: str
    document_id: str
    source_uri: str
    title: str
    text_excerpt: str
    keywords: list[str]
    metadata: dict[str, Any]
    corpus_version: str


DEFAULT_CORPUS: list[_CorpusDoc] = [
    {
        "chunk_id": "rb-slo-001",
        "document_id": "doc-slo-regression",
        "source_uri": "kb://runbooks/slo-regression",
        "title": "SLO regression triage",
        "text_excerpt": (
            "When error rate and latency spike together, check recent deploys and dependency health. "
            "Correlate metrics window with change events."
        ),
        "keywords": ["latency", "error", "slo", "spike", "deploy", "incident"],
        "metadata": {"document_type": "runbook", "team": "platform"},
        "corpus_version": "phase5_local_v1",
    },
    {
        "chunk_id": "rb-cap-002",
        "document_id": "doc-capacity",
        "source_uri": "kb://runbooks/capacity",
        "title": "Capacity saturation",
        "text_excerpt": (
            "Saturation patterns include queue depth growth and timeout cascades. "
            "Validate autoscaling limits and downstream quotas."
        ),
        "keywords": ["capacity", "saturation", "queue", "timeout", "quota"],
        "metadata": {"document_type": "runbook", "team": "platform"},
        "corpus_version": "phase5_local_v1",
    },
    {
        "chunk_id": "rb-config-003",
        "document_id": "doc-config-drift",
        "source_uri": "kb://runbooks/config-drift",
        "title": "Configuration drift",
        "text_excerpt": (
            "Config drift often follows partial rollouts. Compare effective config revision across instances."
        ),
        "keywords": ["config", "drift", "rollout", "incident"],
        "metadata": {"document_type": "runbook", "team": "platform"},
        "corpus_version": "phase5_local_v1",
    },
    {
        "chunk_id": "cost-bill-001",
        "document_id": "doc-billing-anomaly",
        "source_uri": "kb://billing/anomaly-playbook",
        "title": "Spend anomaly investigation",
        "text_excerpt": (
            "Compare daily spend against trailing baseline. Attribute spikes to service, team, and region. "
            "Cross-check usage metrics and reserved capacity changes."
        ),
        "keywords": ["cost", "billing", "spend", "anomaly", "attribution", "usage", "metrics"],
        "metadata": {"document_type": "playbook", "team": "finops", "workflow": "cost_attribution"},
        "corpus_version": "phase5_local_v1",
    },
    {
        "chunk_id": "cost-opt-002",
        "document_id": "doc-optimization",
        "source_uri": "kb://billing/optimization",
        "title": "Cost optimization candidates",
        "text_excerpt": (
            "Review idle resources, oversized instances, and egress-heavy services. "
            "Prioritize rightsizing and autoscaling policy tuning."
        ),
        "keywords": ["optimization", "rightsizing", "idle", "egress", "autoscaling", "cost"],
        "metadata": {"document_type": "playbook", "team": "finops", "workflow": "cost_attribution"},
        "corpus_version": "phase5_local_v1",
    },
]


def _query_tokens(query: str) -> set[str]:
    return {t for t in re.findall(r"[a-zA-Z0-9_]{2,}", query.lower())}


def _term_freq(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-zA-Z0-9_]{3,}", text.lower()))


def _cosine_similarity(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b.get(t, 0) for t in a)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _metadata_matches(doc_meta: dict[str, Any], filters: dict[str, Any]) -> bool:
    for key, expected in filters.items():
        if key in ("corpus_version",):
            continue
        if expected is None:
            continue
        actual = doc_meta.get(key)
        if actual is None:
            return False
        if str(actual) != str(expected):
            return False
    return True


def filter_corpus(
    corpus: list[_CorpusDoc],
    *,
    filters: dict[str, Any],
    corpus_version: str | None,
) -> list[_CorpusDoc]:
    out: list[_CorpusDoc] = []
    for doc in corpus:
        doc_version = str(doc.get("corpus_version") or "")
        if corpus_version and doc_version and doc_version != corpus_version:
            continue
        meta = doc.get("metadata") or {}
        if isinstance(meta, dict) and filters and not _metadata_matches(meta, filters):
            continue
        out.append(doc)
    return out if out else list(corpus)


def score_and_rank(
    query: str,
    corpus: list[_CorpusDoc],
    max_results: int,
) -> list[EvidenceChunk]:
    tokens = _query_tokens(query)
    q_tf = _term_freq(query)
    scored: list[tuple[float, _CorpusDoc]] = []
    for doc in corpus:
        kws = {k.lower() for k in doc.get("keywords", [])}
        overlap = len(tokens & kws)
        title = str(doc.get("title") or "")
        title_hit = title.lower() in query.lower() or any(t in title.lower() for t in tokens)
        body_tf = _term_freq(f"{title} {doc.get('text_excerpt', '')}")
        semantic = _cosine_similarity(q_tf, body_tf)
        score = float(overlap) + (0.5 if title_hit else 0.0) + semantic * 2.0
        if score > 0:
            scored.append((score, doc))
    scored.sort(key=lambda x: (-x[0], x[1]["chunk_id"]))
    out: list[EvidenceChunk] = []
    for s, doc in scored[:max_results]:
        norm = min(1.0, s / 5.0)
        meta = doc.get("metadata") or {}
        out.append(
            EvidenceChunk(
                chunk_id=doc["chunk_id"],
                document_id=doc.get("document_id"),
                source_uri=doc["source_uri"],
                title=title or None,
                text_excerpt=doc["text_excerpt"],
                score=round(norm, 3),
                corpus_version=doc.get("corpus_version"),
                metadata=dict(meta) if isinstance(meta, dict) else {},
            ),
        )
    if not out and corpus:
        doc = corpus[0]
        meta = doc.get("metadata") or {}
        out.append(
            EvidenceChunk(
                chunk_id=doc["chunk_id"],
                document_id=doc.get("document_id"),
                source_uri=doc["source_uri"],
                title=str(doc.get("title") or "") or None,
                text_excerpt=doc["text_excerpt"],
                score=0.1,
                corpus_version=doc.get("corpus_version"),
                metadata=dict(meta) if isinstance(meta, dict) else {},
            ),
        )
    return out[:max_results]


def retrieve_from_corpus(
    request: RetrievalRequest,
    corpus: list[dict[str, Any]],
) -> tuple[list[EvidenceChunk], str]:
    normalized: list[_CorpusDoc] = []
    for raw in corpus:
        normalized.append(
            {
                "chunk_id": str(raw["chunk_id"]),
                "document_id": str(raw.get("document_id") or raw["chunk_id"]),
                "source_uri": str(raw["source_uri"]),
                "title": str(raw.get("title") or ""),
                "text_excerpt": str(raw["text_excerpt"]),
                "keywords": [str(k) for k in raw.get("keywords", [])],
                "metadata": dict(raw.get("metadata") or {}),
                "corpus_version": str(raw.get("corpus_version") or "phase5_local_v1"),
            },
        )
    version = request.corpus_version or (
        str(normalized[0].get("corpus_version")) if normalized else "phase5_local_v1"
    )
    scoped = filter_corpus(normalized, filters=request.filters, corpus_version=request.corpus_version)
    chunks = score_and_rank(request.query, scoped, request.max_results)
    return chunks, version
