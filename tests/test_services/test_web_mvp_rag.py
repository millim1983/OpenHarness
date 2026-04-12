from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from openharness.config.settings import ProviderProfile, Settings
from openharness.services.rag_store import RagStore
from openharness.services.rag_types import ChunkRecord, IndexedDocument


class FakeEmbeddingBackend:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeChatStore:
    def list_documents(self) -> list[IndexedDocument]:
        return [IndexedDocument(id=1, file_name="notice.txt", content_hash="abc", chunk_count=1)]

    def load_all_chunks(self) -> list[ChunkRecord]:
        return [
            ChunkRecord(
                id=1,
                document_id=1,
                chunk_index=0,
                text="The application deadline is Friday at 18:00.",
                start_char=0,
                end_char=44,
                embedding=[1.0, 0.0],
            )
        ]

    def get_document_metadata(self, document_id: int) -> dict[str, object]:
        assert document_id == 1
        return {
            "embedding_profile": "openai-compatible",
            "chat_profile": "gemini-compatible",
            "document_type": "announcement",
            "title": "Funding notice",
            "ministry": "Industry Ministry",
            "agency": "Program office",
            "rd_or_non_rd": "non_rd",
            "business_type": "Commercialization",
            "submission_deadline": "Friday at 18:00",
        }

    def get_file_name(self, document_id: int) -> str:
        assert document_id == 1
        return "notice.txt"

    def get_document_artifact(self, document_id: int) -> dict[str, object]:
        assert document_id == 1
        return {}

    def load_chunks_for_document(self, document_id: int) -> list[ChunkRecord]:
        assert document_id == 1
        return self.load_all_chunks()


def load_web_mvp_server():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "web_mvp_server.py"
    spec = importlib.util.spec_from_file_location("web_mvp_server", module_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def settings_with_profiles() -> Settings:
    return Settings(
        active_profile="gemini-compatible",
        profiles={
            "gemini-compatible": ProviderProfile(
                label="Gemini Compatible",
                provider="gemini",
                api_format="openai",
                auth_source="openai_api_key",
                default_model="gemini-2.5-pro",
                base_url="https://example.test/v1",
            ),
            "openai-compatible": ProviderProfile(
                label="OpenAI Compatible",
                provider="openai",
                api_format="openai",
                auth_source="openai_api_key",
                default_model="gpt-5.4",
            ),
        },
    )


def test_run_chat_attaches_rag_context(monkeypatch) -> None:
    module = load_web_mvp_server()
    captured: dict[str, str] = {}

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(
        module.RagStore, "for_project", classmethod(lambda cls, cwd: FakeChatStore())
    )

    def fake_run_single_prompt_sync(
        *, profile_name: str, message: str, cwd: str, system_prompt: str = ""
    ) -> dict[str, str]:
        captured["profile_name"] = profile_name
        captured["message"] = message
        captured["cwd"] = cwd
        captured["system_prompt"] = system_prompt
        return {"profile": profile_name, "answer": "Use Friday."}

    monkeypatch.setattr(module, "run_single_prompt_sync", fake_run_single_prompt_sync)

    result = module._run_chat("gemini-compatible", "When is the deadline?")

    assert result["rag"]["enabled"] is True
    assert result["rag"]["retrieved_chunk_count"] == 1
    assert result["rag"]["sources"][0]["document_type"] == "announcement"
    assert result["rag"]["sources"][0]["rd_or_non_rd"] == "non_rd"
    assert "Retrieved document context" in captured["message"]
    assert "notice.txt#0" in captured["message"]
    assert "When is the deadline?" in captured["message"]


def test_run_chat_applies_rag_filters(monkeypatch) -> None:
    module = load_web_mvp_server()
    captured: dict[str, str] = {}

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(
        module.RagStore, "for_project", classmethod(lambda cls, cwd: FakeChatStore())
    )

    def fake_run_single_prompt_sync(
        *, profile_name: str, message: str, cwd: str, system_prompt: str = ""
    ) -> dict[str, str]:
        captured["message"] = message
        return {"profile": profile_name, "answer": "No matching context."}

    monkeypatch.setattr(module, "run_single_prompt_sync", fake_run_single_prompt_sync)

    result = module._run_chat(
        "gemini-compatible",
        "When is the deadline?",
        module.RagRetrievalFilters(document_type="technical"),
    )

    assert result["rag"]["enabled"] is False
    assert result["rag"]["retrieved_chunk_count"] == 0
    assert result["rag"]["applied_filters"] == {
        "document_type": "technical",
        "ministry": "",
        "agency": "",
        "rd_or_non_rd": "",
        "business_type": "",
    }
    assert "Retrieved document context" not in captured["message"]


def test_index_document_for_rag_returns_document_status(tmp_path: Path, monkeypatch) -> None:
    module = load_web_mvp_server()
    store = RagStore(tmp_path / "rag.sqlite3")

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(module.RagStore, "for_project", classmethod(lambda cls, cwd: store))

    status = module._index_document_for_rag(
        chat_profile_name="gemini-compatible",
        file_name="notice.txt",
        extracted_text="Budget support is available.\n\nThe application deadline is Friday.",
        instruction="Focus on deadlines.",
        team_context="Alex PM: submission",
    )

    assert status["enabled"] is True
    assert status["embedding_profile"] == "openai-compatible"
    assert status["indexed_document_count"] == 1
    assert status["indexed_chunk_count"] >= 1
    assert status["ingestion_source_id"] > 0
    assert status["ingestion_review_item_id"] > 0
    assert status["documents"][0]["file_name"] == "notice.txt"
    assert status["documents"][0]["document_type"] == "announcement"
    assert status["documents"][0]["title"] == "Budget support is available."


def test_run_document_summary_stores_detail_artifact(tmp_path: Path, monkeypatch) -> None:
    module = load_web_mvp_server()
    store = RagStore(tmp_path / "rag.sqlite3")

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(module.RagStore, "for_project", classmethod(lambda cls, cwd: store))
    monkeypatch.setenv("OPENHARNESS_PROPOSAL_OUTPUT_DIR", str(tmp_path / "proposal_outputs"))

    monkeypatch.setattr(
        module,
        "run_announcement_analysis",
        lambda *args, **kwargs: SimpleNamespace(
            workflow_name="announcement_analysis",
            summary="Stored summary",
            structured={
                "announcement_overview": {"title": "Stored notice"},
                "internal_execution_plan": {"immediate_next_actions": ["Call owner"]},
            },
            prompt_source_truncated=False,
        ),
    )

    result = module._run_document_summary(
        "gemini-compatible",
        "notice.txt",
        base64.b64encode(b"Application deadline is Friday.").decode("ascii"),
        "Use stored instruction",
        "Alex PM",
        "Use stored system prompt",
    )
    detail = module._get_rag_document_detail(result["rag"]["indexed_document_id"])

    assert detail["artifact_available"] is True
    assert detail["summary"] == "Stored summary"
    assert detail["structured"]["internal_execution_plan"]["immediate_next_actions"] == [
        "Call owner"
    ]
    assert result["proposal_ops"]["project_summary"]["title"] == "Stored notice"
    assert "folder_plan" in result["proposal_ops"]
    assert result["announcement_agent"]["enabled"] is True
    assert result["announcement_agent"]["summary_workbook"].endswith("총괄장.xlsx")


def test_run_announcement_agent_bundle_handles_folder_upload(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_web_mvp_server()
    store = RagStore(tmp_path / "rag.sqlite3")

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(module.RagStore, "for_project", classmethod(lambda cls, cwd: store))
    monkeypatch.setenv("OPENHARNESS_PROPOSAL_OUTPUT_DIR", str(tmp_path / "proposal_outputs"))

    extracted_file_names: list[str] = []

    def fake_extract_text(file_name: str, file_bytes: bytes) -> str:
        extracted_file_names.append(file_name)
        if not file_name.endswith(".pdf"):
            raise AssertionError(f"Non-notice attachment should not be parsed: {file_name}")
        return file_bytes.decode("utf-8")

    monkeypatch.setattr(
        module,
        "extract_text_from_document",
        fake_extract_text,
    )
    monkeypatch.setattr(
        module,
        "run_announcement_analysis",
        lambda *args, **kwargs: SimpleNamespace(
            workflow_name="announcement_analysis",
            summary="Bundle summary",
            structured={
                "announcement_overview": {
                    "title": "AI Platform",
                    "project_type": "R&D",
                    "ministry": "과학기술정보통신부",
                    "professional_agency": "정보통신기획평가원",
                    "main_purpose": "AI",
                },
                "application_schedule": {"submission_deadline": "2026-07-03 18:00"},
            },
            prompt_source_truncated=False,
        ),
    )

    result = module._run_announcement_agent_bundle(
        profile_name="gemini-compatible",
        files=[
            {
                "file_name": "공고.pdf",
                "relative_path": "upload_set/공고.pdf",
                "file_data_base64": base64.b64encode(
                    "공고 AI Platform deadline\n전문기관: 정보통신기획평가원".encode("utf-8")
                ).decode("ascii"),
            },
            {
                "file_name": "form.hwp",
                "relative_path": "upload_set/forms/form.hwp",
                "file_data_base64": base64.b64encode(b"Required form").decode("ascii"),
            },
        ],
        instruction="Extract announcement fields.",
        team_context="PM: submission",
        system_prompt="Classify business domain.",
    )

    project_dir = Path(result["announcement_agent"]["project_dir"])

    assert result["file_count"] == 2
    assert result["primary_file_name"] == "공고.pdf"
    assert result["primary_relative_path"] == "upload_set/공고.pdf"
    assert result["structured"]["announcement_overview"]["professional_agency"] == "정보통신기획평가원"
    assert extracted_file_names == ["공고.pdf"]
    assert len(result["announcement_agent"]["saved_source_files"]) == 2
    assert (project_dir / "upload_set" / "forms" / "form.hwp").exists()
    assert Path(result["announcement_agent"]["attachment_manifest"]).exists()
    assert result["announcement_agent"]["summary_workbook"].endswith("총괄장.xlsx")
    assert Path(result["announcement_agent"]["monitoring_workbook"]).name.startswith(
        "공고리스트_"
    )
    assert result["announcement_agent"]["dashboard_stats"]["by_business_domain"] == {"AI": 1}
    assert result["announcement_agent"]["monitoring_row"]["agency"] == "IITP"
    assert result["rag"]["indexed_document_count"] == 1
    detail = module._get_rag_document_detail(result["rag"]["indexed_document_id"])
    assert detail["structured"]["announcement_overview"]["professional_agency"] == "정보통신기획평가원"
    assert result["attachment_files"][0]["role"] == "notice_pdf"
    assert result["attachment_files"][1]["role"] == "attachment"
    assert result["attachment_files"][1]["indexed"] is False


def test_run_announcement_agent_bundle_requires_notice_pdf(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_web_mvp_server()
    store = RagStore(tmp_path / "rag.sqlite3")

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(module.RagStore, "for_project", classmethod(lambda cls, cwd: store))

    with pytest.raises(ValueError, match="PDF 공고"):
        module._run_announcement_agent_bundle(
            profile_name="gemini-compatible",
            files=[
                {
                    "file_name": "form.txt",
                    "relative_path": "upload_set/form.txt",
                    "file_data_base64": base64.b64encode(b"Required form").decode("ascii"),
                }
            ],
            instruction="Extract announcement fields.",
            team_context="PM: submission",
            system_prompt="Classify business domain.",
        )


def test_ingestion_state_and_review_update_helpers(tmp_path: Path, monkeypatch) -> None:
    module = load_web_mvp_server()
    store = RagStore(tmp_path / "rag.sqlite3")

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(module.RagStore, "for_project", classmethod(lambda cls, cwd: store))

    indexed = module._index_document_for_rag(
        chat_profile_name="gemini-compatible",
        file_name="notice.txt",
        extracted_text="Budget support is available.\n\nThe application deadline is Friday.",
        instruction="Focus on deadlines.",
        team_context="Alex PM: submission",
    )

    state = module._ingestion_state()
    assert state["summary"]["source_count"] == 1
    assert state["summary"]["review_item_count"] == 1
    assert state["summary"]["needs_review_count"] == 1
    assert state["sources"][0]["source_type"] == "upload"
    assert state["review_items"][0]["document_id"] == indexed["indexed_document_id"]

    updated = module._update_ingestion_review_item(
        {
            "review_item_id": indexed["ingestion_review_item_id"],
            "review_status": "approved",
            "notes": "Reviewed in dashboard.",
        }
    )

    assert updated["summary"]["approved_count"] == 1
    assert updated["review_items"][0]["review_status"] == "approved"
    assert updated["review_items"][0]["notes"] == "Reviewed in dashboard."


def test_rag_document_management_helpers(tmp_path: Path, monkeypatch) -> None:
    module = load_web_mvp_server()
    store = RagStore(tmp_path / "rag.sqlite3")

    monkeypatch.setattr(module, "load_settings", settings_with_profiles)
    monkeypatch.setattr(
        module,
        "create_embedding_backend_for_profile",
        lambda *args, **kwargs: FakeEmbeddingBackend(),
    )
    monkeypatch.setattr(module.RagStore, "for_project", classmethod(lambda cls, cwd: store))

    indexed = module._index_document_for_rag(
        chat_profile_name="gemini-compatible",
        file_name="notice.txt",
        extracted_text="Budget support is available.\n\nThe application deadline is Friday.",
        instruction="Focus on deadlines.",
        team_context="Alex PM: submission",
    )
    document_id = indexed["indexed_document_id"]

    listed = module._list_rag_documents()
    assert listed["indexed_document_count"] == 1
    assert listed["documents"][0]["file_name"] == "notice.txt"

    reindexed = module._reindex_rag_document(document_id, "gemini-compatible")
    assert reindexed["reindexed_document_id"] == document_id
    assert reindexed["embedding_profile"] == "openai-compatible"

    deleted = module._delete_rag_document(document_id)
    assert deleted["deleted_document_id"] == document_id
    assert deleted["indexed_document_count"] == 0
