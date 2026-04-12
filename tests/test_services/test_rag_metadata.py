from __future__ import annotations

from openharness.services.rag_metadata import (
    build_rag_document_metadata,
    classify_document_type,
    enrich_metadata_for_index,
)


def test_build_rag_document_metadata_extracts_announcement_fields() -> None:
    metadata = build_rag_document_metadata(
        file_name="notice.pdf",
        extracted_text="중소벤처기업부 공고\n사업화 지원사업\n신청은 온라인으로 접수합니다.",
        embedding_profile="openai-compatible",
        chat_profile="gemini-compatible",
        instruction="Focus on deadlines.",
        has_team_context=True,
        structured_analysis={
            "announcement_overview": {
                "title": "사업화 지원사업 공고",
                "project_type": "Commercialization",
            },
            "application_schedule": {
                "submission_deadline": "2026-04-17 18:00",
            },
            "submission_channel": {
                "method": "온라인 접수",
                "portal_or_address": "example.go.kr",
            },
            "contacts": [
                {
                    "organization": "중소벤처기업부",
                    "name": "Kim",
                    "phone": "02-0000-0000",
                    "email": "",
                    "topic": "사업 문의",
                }
            ],
            "eligibility_by_role": [{"role": "lead"}],
        },
    )

    assert metadata["metadata_schema_version"] == 1
    assert metadata["document_type"] == "announcement"
    assert metadata["title"] == "사업화 지원사업 공고"
    assert metadata["embedding_profile"] == "openai-compatible"
    assert metadata["chat_profile"] == "gemini-compatible"
    assert metadata["business_type"] == "Commercialization"
    assert metadata["submission_deadline"] == "2026-04-17 18:00"
    assert metadata["announcement"]["submission_channel"] == "온라인 접수 example.go.kr"
    assert metadata["announcement"]["eligibility_roles"] == ["lead"]


def test_build_rag_document_metadata_prefers_labeled_organizations() -> None:
    metadata = build_rag_document_metadata(
        file_name="notice.txt",
        extracted_text=(
            "2026 사업화 지원사업 공고\n"
            "주관부처: 산업통상자원부\n"
            "전담기관: 한국산업기술진흥원\n"
            "사업유형: Commercialization\n"
            "구분: 비R&D 사업화 지원\n"
        ),
        structured_analysis={
            "announcement_overview": {
                "title": "2026 사업화 지원사업 공고",
                "project_type": "Commercialization",
            },
        },
    )

    assert metadata["ministry"] == "산업통상자원부"
    assert metadata["agency"] == "한국산업기술진흥원"
    assert metadata["rd_or_non_rd"] == "non_rd"


def test_classify_document_type_detects_non_announcement_documents() -> None:
    assert classify_document_type("policy.md", "시행일: 2026-01-01\n운영요령 및 규정") == "regulation"
    assert classify_document_type("api.md", "Version: 1.2\nAPI specification") == "technical"
    assert (
        classify_document_type("team.md", "Department: Ops\nOwner: Alex\nResponsibility: review")
        == "company_team"
    )


def test_enrich_metadata_for_index_preserves_existing_payload() -> None:
    metadata = enrich_metadata_for_index(
        {"document_type": "announcement", "title": "Notice"},
        content_hash="abc",
        chunk_count=3,
    )

    assert metadata["document_type"] == "announcement"
    assert metadata["title"] == "Notice"
    assert metadata["content_hash"] == "abc"
    assert metadata["chunk_count"] == 3
