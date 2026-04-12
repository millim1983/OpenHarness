from __future__ import annotations

from pathlib import Path

from openharness.services.rag_indexing import chunk_document_text, index_document
from openharness.services.rag_retrieval import build_retrieval_context, retrieve_relevant_chunks
from openharness.services.rag_store import RagStore
from openharness.services.rag_types import RagRetrievalFilters


class FakeEmbeddingBackend:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            lowered = text.lower()
            vectors.append(
                [
                    1.0 if "budget" in lowered else 0.0,
                    1.0 if "deadline" in lowered else 0.0,
                    float(len(lowered) % 7),
                ]
            )
        return vectors


def test_chunk_document_text_keeps_multiple_chunks() -> None:
    text = "\n\n".join(
        [
            "First paragraph about budget and cost matching.",
            "Second paragraph about the application deadline and submission.",
            "Third paragraph with general notes.",
        ]
    )

    chunks = chunk_document_text(text, chunk_size_chars=70, overlap_chars=10)

    assert len(chunks) >= 2
    assert chunks[0].text
    assert chunks[0].end_char >= chunks[0].start_char


def test_index_and_retrieve_document(tmp_path: Path) -> None:
    store = RagStore(tmp_path / "rag.sqlite3")
    backend = FakeEmbeddingBackend()

    document_id = index_document(
        cwd=str(tmp_path),
        file_name="notice.txt",
        extracted_text=(
            "Budget support is available for prototype work.\n\n"
            "The final application deadline is April 17 at 18:00.\n\n"
            "Questions should go to the program office."
        ),
        embedding_backend=backend,
        store=store,
    )

    assert document_id > 0
    assert store.list_documents()[0].chunk_count >= 1

    results = retrieve_relevant_chunks(
        cwd=str(tmp_path),
        query="What is the application deadline?",
        embedding_backend=backend,
        store=store,
        top_k=2,
    )

    assert results
    assert results[0].file_name == "notice.txt"
    context = build_retrieval_context(results)
    assert "notice.txt" in context

    store.upsert_document_artifact(
        document_id,
        extracted_text="Full extracted text",
        summary="Summary text",
        structured={"answer": "structured"},
        workflow_name="announcement_analysis",
        prompt_source_truncated=False,
    )
    artifact = store.get_document_artifact(document_id)
    assert artifact["extracted_text"] == "Full extracted text"
    assert artifact["structured"] == {"answer": "structured"}


def test_retrieve_relevant_chunks_filters_by_metadata(tmp_path: Path) -> None:
    store = RagStore(tmp_path / "rag.sqlite3")
    backend = FakeEmbeddingBackend()

    index_document(
        cwd=str(tmp_path),
        file_name="notice.txt",
        extracted_text="The application deadline is Friday.",
        embedding_backend=backend,
        store=store,
        metadata={
            "document_type": "announcement",
            "title": "Funding notice",
            "ministry": "Industry Ministry",
            "agency": "Program Office",
            "rd_or_non_rd": "non_rd",
            "business_type": "Commercialization",
        },
    )
    index_document(
        cwd=str(tmp_path),
        file_name="spec.md",
        extracted_text="The API deadline behavior is documented here.",
        embedding_backend=backend,
        store=store,
        metadata={
            "document_type": "technical",
            "title": "API spec",
            "business_type": "Platform",
        },
    )

    results = retrieve_relevant_chunks(
        cwd=str(tmp_path),
        query="deadline",
        embedding_backend=backend,
        store=store,
        top_k=5,
        filters=RagRetrievalFilters(document_type="announcement", business_type="Commercial"),
    )

    assert [result.file_name for result in results] == ["notice.txt"]
    assert results[0].document_type == "announcement"
    assert results[0].title == "Funding notice"
    assert results[0].rd_or_non_rd == "non_rd"
