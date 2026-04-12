from __future__ import annotations

import json
from pathlib import Path

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.rag_document_tools import (
    RagGetDocumentTool,
    RagGetDocumentToolInput,
    RagListDocumentsTool,
    RagListDocumentsToolInput,
)


def test_default_registry_includes_rag_tools() -> None:
    registry = create_default_tool_registry()
    names = {tool.name for tool in registry.list_tools()}

    assert "rag_search" in names
    assert "rag_list_documents" in names
    assert "rag_get_document" in names


async def test_rag_document_tools_read_project_store(tmp_path: Path, monkeypatch) -> None:
    from openharness.services.rag_store import RagStore

    store = RagStore(tmp_path / "rag.sqlite3")
    document_id = store.upsert_document(
        "notice.txt",
        "abc123",
        metadata={"document_type": "announcement", "title": "Funding notice"},
    )
    store.upsert_document_artifact(
        document_id,
        extracted_text="Funding notice text",
        summary="Funding notice summary",
        structured={"announcement_overview": {"title": "Funding notice"}},
        workflow_name="announcement_analysis",
        prompt_source_truncated=False,
    )

    monkeypatch.setattr(RagStore, "for_project", classmethod(lambda cls, cwd: store))
    context = ToolExecutionContext(cwd=tmp_path)

    list_result = await RagListDocumentsTool().execute(RagListDocumentsToolInput(), context)
    listed = json.loads(list_result.output)
    assert listed["documents"][0]["id"] == document_id
    assert listed["documents"][0]["metadata"]["document_type"] == "announcement"

    get_result = await RagGetDocumentTool().execute(
        RagGetDocumentToolInput(document_id=document_id, include_chunks=False),
        context,
    )
    detail = json.loads(get_result.output)
    assert detail["file_name"] == "notice.txt"
    assert detail["summary"] == "Funding notice summary"
