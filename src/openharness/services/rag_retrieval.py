"""Retrieval helpers for the local RAG store."""

from __future__ import annotations

from math import sqrt

from openharness.services.rag_store import RagStore
from openharness.services.rag_types import EmbeddingBackend, RagRetrievalFilters, RetrievedChunk


def retrieve_relevant_chunks(
    *,
    cwd: str,
    query: str,
    embedding_backend: EmbeddingBackend,
    store: RagStore | None = None,
    top_k: int = 5,
    filters: RagRetrievalFilters | None = None,
) -> list[RetrievedChunk]:
    """Return top-k relevant chunks using cosine similarity."""
    if not query.strip():
        return []

    rag_store = store or RagStore.for_project(cwd)
    query_vectors = embedding_backend.embed_texts([query])
    if not query_vectors:
        return []
    query_vector = query_vectors[0]

    scored: list[RetrievedChunk] = []
    metadata_cache: dict[int, dict[str, object]] = {}
    for chunk in rag_store.load_all_chunks():
        metadata = metadata_cache.get(chunk.document_id)
        if metadata is None:
            metadata = rag_store.get_document_metadata(chunk.document_id)
            metadata_cache[chunk.document_id] = metadata
        if filters is not None and not _metadata_matches_filters(metadata, filters):
            continue
        score = _cosine_similarity(query_vector, chunk.embedding)
        if score <= 0:
            continue
        scored.append(
            RetrievedChunk(
                document_id=chunk.document_id,
                file_name=rag_store.get_file_name(chunk.document_id),
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                score=score,
                title=_metadata_string(metadata, "title"),
                document_type=_metadata_string(metadata, "document_type") or "unknown",
                ministry=_metadata_string(metadata, "ministry"),
                agency=_metadata_string(metadata, "agency"),
                rd_or_non_rd=_metadata_string(metadata, "rd_or_non_rd"),
                business_type=_metadata_string(metadata, "business_type"),
            )
        )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:top_k]


def build_retrieval_context(chunks: list[RetrievedChunk]) -> str:
    """Render retrieved chunks into a prompt-friendly context block."""
    if not chunks:
        return ""
    lines = ["Retrieved document context:"]
    for chunk in chunks:
        lines.append(f"[{chunk.file_name}#{chunk.chunk_index} score={chunk.score:.3f}]")
        lines.append(chunk.text)
        lines.append("")
    return "\n".join(lines).strip()


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _metadata_matches_filters(
    metadata: dict[str, object], filters: RagRetrievalFilters
) -> bool:
    if not filters.has_values():
        return True
    for key, expected in filters.as_dict().items():
        expected = expected.strip()
        if not expected:
            continue
        actual = _metadata_string(metadata, key)
        if key == "document_type":
            if actual.casefold() != expected.casefold():
                return False
            continue
        if expected.casefold() not in actual.casefold():
            return False
    return True


def _metadata_string(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key, "")
    return value.strip() if isinstance(value, str) else ""
