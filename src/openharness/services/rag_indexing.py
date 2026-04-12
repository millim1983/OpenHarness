"""Chunking and indexing pipeline for local document RAG."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from openharness.services.rag_metadata import enrich_metadata_for_index
from openharness.services.rag_store import RagStore
from openharness.services.rag_types import ChunkRecord, EmbeddingBackend


DEFAULT_CHUNK_SIZE_CHARS = 1200
DEFAULT_CHUNK_OVERLAP_CHARS = 160


@dataclass(frozen=True)
class ChunkSpec:
    """Prepared chunk text plus offsets before storage."""

    chunk_index: int
    text: str
    start_char: int
    end_char: int


def chunk_document_text(
    text: str,
    *,
    chunk_size_chars: int = DEFAULT_CHUNK_SIZE_CHARS,
    overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> list[ChunkSpec]:
    """Split document text into paragraph-aware overlapping chunks."""
    cleaned = text.strip()
    if not cleaned:
        return []

    paragraphs = [paragraph.strip() for paragraph in cleaned.split("\n\n") if paragraph.strip()]
    chunks: list[ChunkSpec] = []
    cursor = 0
    current = ""
    current_start = 0

    def _flush() -> None:
        nonlocal current, current_start
        if not current.strip():
            current = ""
            return
        chunk_text = current.strip()
        chunk_end = current_start + len(chunk_text)
        chunks.append(
            ChunkSpec(
                chunk_index=len(chunks),
                text=chunk_text,
                start_char=current_start,
                end_char=chunk_end,
            )
        )
        if overlap_chars > 0 and len(chunk_text) > overlap_chars:
            overlap_text = chunk_text[-overlap_chars:]
            current = overlap_text
            current_start = max(chunk_end - len(overlap_text), 0)
        else:
            current = ""
            current_start = chunk_end

    for paragraph in paragraphs:
        if not current:
            current = paragraph
            current_start = cursor
        elif len(current) + 2 + len(paragraph) <= chunk_size_chars:
            current = f"{current}\n\n{paragraph}"
        else:
            _flush()
            if len(paragraph) <= chunk_size_chars:
                current = f"{current}\n\n{paragraph}".strip() if current else paragraph
            else:
                slices = _split_long_paragraph(paragraph, chunk_size_chars, overlap_chars)
                for slice_text in slices[:-1]:
                    slice_start = cursor
                    slice_end = slice_start + len(slice_text)
                    chunks.append(
                        ChunkSpec(
                            chunk_index=len(chunks),
                            text=slice_text,
                            start_char=slice_start,
                            end_char=slice_end,
                        )
                    )
                    cursor = slice_end - overlap_chars if overlap_chars > 0 else slice_end
                current = slices[-1]
                current_start = cursor
        cursor += len(paragraph) + 2

    _flush()
    return [chunk for chunk in chunks if chunk.text.strip()]


def _split_long_paragraph(paragraph: str, chunk_size_chars: int, overlap_chars: int) -> list[str]:
    slices: list[str] = []
    start = 0
    while start < len(paragraph):
        end = min(len(paragraph), start + chunk_size_chars)
        slices.append(paragraph[start:end].strip())
        if end >= len(paragraph):
            break
        start = max(end - overlap_chars, start + 1)
    return [slice_text for slice_text in slices if slice_text]


def index_document(
    *,
    cwd: str,
    file_name: str,
    extracted_text: str,
    embedding_backend: EmbeddingBackend,
    metadata: dict[str, object] | None = None,
    store: RagStore | None = None,
    chunk_size_chars: int = DEFAULT_CHUNK_SIZE_CHARS,
    overlap_chars: int = DEFAULT_CHUNK_OVERLAP_CHARS,
) -> int:
    """Chunk, embed, and persist one document."""
    chunks = chunk_document_text(
        extracted_text,
        chunk_size_chars=chunk_size_chars,
        overlap_chars=overlap_chars,
    )
    if not chunks:
        raise ValueError("Cannot index an empty document.")

    vectors = embedding_backend.embed_texts([chunk.text for chunk in chunks])
    if len(vectors) != len(chunks):
        raise RuntimeError("Embedding backend returned an unexpected number of vectors.")

    rag_store = store or RagStore.for_project(cwd)
    content_hash = sha1(extracted_text.encode("utf-8")).hexdigest()
    document_id = rag_store.upsert_document(
        file_name,
        content_hash,
        metadata=enrich_metadata_for_index(
            metadata,
            content_hash=content_hash,
            chunk_count=len(chunks),
        ),
    )
    rag_store.insert_chunks(
        document_id,
        [
            ChunkRecord(
                id=0,
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors)
        ],
    )
    return document_id
