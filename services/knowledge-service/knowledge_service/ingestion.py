"""Deterministic document ingestion and chunking (Session D)."""

from __future__ import annotations

import hashlib
import re
from typing import Any


def chunk_text(
    text: str,
    *,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[str]:
    """Split text into overlapping windows; deterministic and explainable."""
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []
    if len(normalized) <= chunk_size:
        return [normalized]
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        chunks.append(normalized[start:end])
        if end >= len(normalized):
            break
        start = max(0, end - overlap)
    return chunks


def _tokenize_keywords(text: str, *, max_keywords: int = 24) -> list[str]:
    tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9_]{3,}", text.lower())}
    return sorted(tokens)[:max_keywords]


def ingest_document(
    *,
    document_id: str,
    source_uri: str,
    title: str,
    text: str,
    metadata: dict[str, Any] | None = None,
    corpus_version: str,
    chunk_size: int = 400,
    overlap: int = 50,
) -> list[dict[str, Any]]:
    """Produce corpus rows (one per chunk) ready for retrieval indexing."""
    meta = dict(metadata or {})
    parts = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not parts:
        parts = [""]
    rows: list[dict[str, Any]] = []
    for idx, excerpt in enumerate(parts):
        digest = hashlib.sha256(f"{document_id}:{idx}:{excerpt}".encode()).hexdigest()[:12]
        chunk_id = f"{document_id}-c{idx}-{digest}"
        rows.append(
            {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "source_uri": source_uri,
                "title": title,
                "text_excerpt": excerpt,
                "keywords": _tokenize_keywords(f"{title} {excerpt}"),
                "metadata": meta,
                "corpus_version": corpus_version,
            },
        )
    return rows
