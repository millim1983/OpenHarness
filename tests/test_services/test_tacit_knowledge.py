from __future__ import annotations

from pathlib import Path

from openharness.services.tacit_knowledge import KnowledgeStore


def test_tacit_knowledge_draft_splits_numbered_memo(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge")
    raw_note = store.create_raw_note(
        "1. 부본을 흑백으로 제출해야 한다. 2. 목표시스템 사용자 시나리오를 보강해야 한다.",
        {
            "business_domain": "SI용역",
            "agency": "한국철도공사",
            "document_type": "RFP",
        },
    )

    cards = store.draft_cards_from_note(raw_note)

    assert len(cards) == 2
    assert cards[0]["knowledge_type"] == "submission_warning"
    assert "pre_submission_review" in cards[0]["workflow_stage"]
    assert cards[0]["business_domain"] == ["SI용역"]
    assert cards[1]["display"]["surface_as"] == "writing_guidance"


def test_tacit_knowledge_save_cards_writes_relations(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge")
    raw_note = store.create_raw_note(
        "수요기관이 연구비를 가져가면 민간부담금 예외 적용 가능 여부를 확인한다.",
        {
            "business_domain": "R&D",
            "ministry": "산업통상자원부",
            "business_type": "수요기관필수",
        },
    )
    cards = store.draft_cards_from_note(raw_note)
    saved = store.save_cards(cards)
    state = store.state()

    assert saved[0]["verification"]["status"] == "confirmed"
    assert saved[0]["knowledge_type"] == "domain_rule"
    assert state["card_count"] == 1
    assert any(edge["to_id"] == "산업통상자원부" for edge in state["relations"])


def test_tacit_knowledge_matches_submission_warning(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge")
    raw_note = store.create_raw_note(
        "부본을 흑백으로 제출해야 한다.",
        {
            "business_domain": "SI용역",
            "agency": "한국철도공사",
            "document_type": "RFP",
        },
    )
    store.save_cards(store.draft_cards_from_note(raw_note))

    matches = store.find_matching_cards(
        structured_analysis={
            "metadata": {"agency": "한국철도공사", "business_type": "SI용역"},
            "announcement_overview": {"project_type": "SI용역"},
        },
        extracted_text="제안요청서에는 부본 흑백 제출 조건이 명시되어 있다.",
        workflow_stage="pre_submission_review",
    )

    assert matches["matched_count"] == 1
    assert matches["checklist"][0]["priority"] == "high"
    assert matches["checklist"][0]["knowledge_id"]


def test_tacit_knowledge_matches_demand_org_as_inquiry(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path / "knowledge")
    raw_note = store.create_raw_note(
        "수요기관이 연구비를 가져가면 민간부담금 예외 적용 가능 여부를 확인한다.",
        {
            "business_domain": "R&D",
            "ministry": "산업통상자원부",
            "business_type": "수요기관필수",
        },
    )
    store.save_cards(store.draft_cards_from_note(raw_note))

    matches = store.find_matching_cards(
        structured_analysis={
            "metadata": {"ministry": "산업통상자원부", "business_type": "수요기관필수"},
            "consortium_requirements": {"demand_company_required": True},
            "budget": {"matching_requirement": "민간부담금 필요"},
        },
        extracted_text="수요기관은 공동연구기관으로 참여하며 연구비와 민간부담금을 검토해야 한다.",
        workflow_stage="budget_planning",
    )

    assert matches["matched_count"] == 1
    assert matches["inquiry_items"][0]["knowledge_type"] == "domain_rule"
