"""RAG document inspection tools."""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from openharness.services.rag_store import RagStore
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class RagListDocumentsToolInput(BaseModel):
    """Arguments for listing indexed RAG documents."""

    include_metadata: bool = Field(default=True)


class RagGetDocumentToolInput(BaseModel):
    """Arguments for reading one indexed RAG document."""

    document_id: int = Field(gt=0)
    include_chunks: bool = Field(default=True)
    max_chars: int = Field(default=12000, ge=500, le=50000)


class RagListDocumentsTool(BaseTool):
    """List indexed project-local RAG documents."""

    name = "rag_list_documents"
    description = "List indexed project RAG documents with chunk counts and metadata."
    input_model = RagListDocumentsToolInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return True

    async def execute(
        self, arguments: RagListDocumentsToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        store = RagStore.for_project(context.cwd)
        documents = []
        for document in store.list_documents():
            payload: dict[str, object] = {
                "id": document.id,
                "file_name": document.file_name,
                "content_hash": document.content_hash,
                "chunk_count": document.chunk_count,
            }
            if arguments.include_metadata:
                payload["metadata"] = store.get_document_metadata(document.id)
            documents.append(payload)
        return ToolResult(
            output=json.dumps({"documents": documents}, ensure_ascii=False, indent=2),
            metadata={"document_count": len(documents)},
        )


class RagGetDocumentTool(BaseTool):
    """Read one indexed project-local RAG document."""

    name = "rag_get_document"
    description = "Get one indexed RAG document's metadata, artifact, and optional chunks."
    input_model = RagGetDocumentToolInput

    def is_read_only(self, arguments: BaseModel) -> bool:
        del arguments
        return True

    async def execute(
        self, arguments: RagGetDocumentToolInput, context: ToolExecutionContext
    ) -> ToolResult:
        store = RagStore.for_project(context.cwd)
        metadata = store.get_document_metadata(arguments.document_id)
        artifact = store.get_document_artifact(arguments.document_id)
        payload: dict[str, object] = {
            "id": arguments.document_id,
            "file_name": store.get_file_name(arguments.document_id),
            "metadata": metadata,
            "artifact_available": bool(artifact),
            "summary": artifact.get("summary", ""),
            "structured": artifact.get("structured", {}),
        }
        if arguments.include_chunks:
            chunks = store.load_chunks_for_document(arguments.document_id)
            remaining = arguments.max_chars
            payload["chunks"] = []
            for chunk in chunks:
                if remaining <= 0:
                    break
                text = chunk.text[:remaining]
                remaining -= len(text)
                payload["chunks"].append(
                    {
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "text": text,
                    }
                )
        return ToolResult(
            output=json.dumps(payload, ensure_ascii=False, indent=2),
            metadata={"document_id": arguments.document_id},
        )
