"""RAG search tool for indexed project documents."""

from __future__ import annotations

from pydantic import BaseModel, Field

from openharness.config.settings import load_settings
from openharness.services.rag_embeddings import (
    create_embedding_backend_for_profile,
    select_embedding_profile,
)
from openharness.services.rag_retrieval import build_retrieval_context, retrieve_relevant_chunks
from openharness.services.rag_store import RagStore
from openharness.services.rag_types import RagRetrievalFilters
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class RagSearchToolInput(BaseModel):
    """Arguments for project-local RAG search."""

    query: str = Field(description="Question or search query to retrieve relevant document chunks")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of chunks to return")
    profile: str = Field(default="", description="Optional chat profile used to select embeddings")
    embedding_profile: str = Field(
        default="", description="Optional explicit OpenAI-compatible embedding profile"
    )
    document_type: str = Field(default="", description="Optional document_type metadata filter")
    ministry: str = Field(default="", description="Optional ministry metadata filter")
    agency: str = Field(default="", description="Optional agency metadata filter")
    rd_or_non_rd: str = Field(default="", description="Optional rd_or_non_rd metadata filter")
    business_type: str = Field(default="", description="Optional business_type metadata filter")


class RagSearchTool(BaseTool):
    """Search indexed project-local RAG documents."""

    name = "rag_search"
    description = "Search indexed project RAG documents and return retrieved source chunks."
    input_model = RagSearchToolInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return True

    async def execute(self, arguments: RagSearchToolInput, context: ToolExecutionContext) -> ToolResult:
        settings = load_settings()
        embedding_profile = select_embedding_profile(
            settings,
            chat_profile_name=arguments.profile,
            requested_profile_name=arguments.embedding_profile,
        )
        backend = create_embedding_backend_for_profile(embedding_profile, settings=settings)
        store = RagStore.for_project(context.cwd)
        chunks = retrieve_relevant_chunks(
            cwd=str(context.cwd),
            query=arguments.query,
            embedding_backend=backend,
            store=store,
            top_k=arguments.top_k,
            filters=RagRetrievalFilters(
                document_type=arguments.document_type,
                ministry=arguments.ministry,
                agency=arguments.agency,
                rd_or_non_rd=arguments.rd_or_non_rd,
                business_type=arguments.business_type,
            ),
        )
        if not chunks:
            return ToolResult(
                output="No matching RAG chunks found.",
                metadata={"embedding_profile": embedding_profile, "retrieved_chunk_count": 0},
            )
        return ToolResult(
            output=build_retrieval_context(chunks),
            metadata={
                "embedding_profile": embedding_profile,
                "retrieved_chunk_count": len(chunks),
                "sources": [
                    {
                        "document_id": chunk.document_id,
                        "file_name": chunk.file_name,
                        "chunk_index": chunk.chunk_index,
                        "score": chunk.score,
                        "document_type": chunk.document_type,
                        "title": chunk.title,
                    }
                    for chunk in chunks
                ],
            },
        )
