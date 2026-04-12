"""Shared data models for the local RAG stack."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class IndexedDocument:
    """Metadata stored for one indexed source document."""

    id: int
    file_name: str
    content_hash: str
    chunk_count: int


@dataclass(frozen=True)
class ChunkRecord:
    """One stored document chunk with its embedding payload."""

    id: int
    document_id: int
    chunk_index: int
    text: str
    start_char: int
    end_char: int
    embedding: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class RagRetrievalFilters:
    """Optional metadata filters for retrieval."""

    document_type: str = ""
    ministry: str = ""
    agency: str = ""
    rd_or_non_rd: str = ""
    business_type: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "document_type": self.document_type,
            "ministry": self.ministry,
            "agency": self.agency,
            "rd_or_non_rd": self.rd_or_non_rd,
            "business_type": self.business_type,
        }

    def has_values(self) -> bool:
        return any(value.strip() for value in self.as_dict().values())


@dataclass(frozen=True)
class RetrievedChunk:
    """Ranked chunk returned by retrieval."""

    document_id: int
    file_name: str
    chunk_index: int
    text: str
    score: float
    title: str = ""
    document_type: str = "unknown"
    ministry: str = ""
    agency: str = ""
    rd_or_non_rd: str = ""
    business_type: str = ""


class EmbeddingBackend(Protocol):
    """Backend interface used by indexing and retrieval services."""

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
