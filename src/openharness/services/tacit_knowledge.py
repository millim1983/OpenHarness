"""JSON-backed tacit knowledge store and draft card generator."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from openharness.config.paths import get_project_rag_dir


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_PATH = REPO_ROOT / "proposal_assets" / "config" / "knowledge_categories.json"


def load_knowledge_categories(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(
        config_path
        or os.environ.get("OPENHARNESS_KNOWLEDGE_CATEGORIES_PATH", "")
        or DEFAULT_CONFIG_PATH
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _date_prefix() -> str:
    return datetime.now().strftime("%Y%m%d")


def _ensure_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _next_id(directory: Path, prefix: str) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    date_prefix = _date_prefix()
    existing = sorted(directory.glob(f"{prefix}-{date_prefix}-*.json"))
    return f"{prefix}-{date_prefix}-{len(existing) + 1:03d}"


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _split_memo_items(memo: str) -> list[str]:
    normalized = memo.replace("\r\n", "\n").strip()
    if not normalized:
        return []
    parts = re.split(r"(?:^|\n|\s)(?:\d+[.)]|[-*])\s+", normalized)
    items = [part.strip(" \n\t.;") for part in parts if part.strip(" \n\t.;")]
    if len(items) <= 1:
        sentence_parts = re.split(r"(?<=[.!?。])\s+|\n{2,}", normalized)
        items = [part.strip(" \n\t.;") for part in sentence_parts if part.strip(" \n\t.;")]
    return items or [normalized]


def _keyword_matches(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _default_rule() -> dict[str, Any]:
    return {
        "name": "general_lesson",
        "keywords": [],
        "knowledge_type": "lesson",
        "category": ["업무암묵지"],
        "workflow_stage": ["post_project_retrospective"],
        "surface_as": "checklist",
        "priority": "medium",
    }


def _select_rule(text: str, config: dict[str, Any]) -> dict[str, Any]:
    for rule in config.get("keyword_rules", []):
        keywords = _ensure_list(rule.get("keywords"))
        if keywords and _keyword_matches(text, keywords):
            return dict(rule)
    return _default_rule()


def _display_message(text: str, rule: dict[str, Any]) -> str:
    surface = str(rule.get("surface_as", "checklist"))
    if surface == "inquiry_item":
        return f"{text} 공고/RFP에 명시되지 않으면 문의처 확인 항목으로 올린다."
    if surface == "warning":
        return f"{text} 제출 전 변환본과 최종본에서 반드시 확인한다."
    if surface == "writing_guidance":
        return f"{text} 제안서 본문 작성 시 근거, 사용자, 활용 시나리오가 드러나도록 보강한다."
    return f"{text} 제출 전 체크리스트로 확인한다."


@dataclass
class KnowledgeStore:
    """Filesystem-backed tacit knowledge store."""

    root_dir: Path
    config: dict[str, Any] | None = None

    @classmethod
    def for_project(cls, cwd: str | Path) -> "KnowledgeStore":
        return cls(get_project_rag_dir(cwd) / "knowledge_store")

    def __post_init__(self) -> None:
        self.root_dir = Path(self.root_dir)
        self.config = self.config or load_knowledge_categories()
        for name in ("raw_notes", "lessons", "rules", "facts", "inquiries"):
            (self.root_dir / name).mkdir(parents=True, exist_ok=True)
        relations_path = self.root_dir / "relations.json"
        if not relations_path.exists():
            _write_json(relations_path, [])

    def create_raw_note(self, memo: str, metadata: dict[str, Any]) -> dict[str, Any]:
        if not memo.strip():
            raise ValueError("`memo` is required.")
        note_id = _next_id(self.root_dir / "raw_notes", "RN")
        record = {
            "id": note_id,
            "memo": memo.strip(),
            "metadata": metadata,
            "created_at": _now(),
        }
        _write_json(self.root_dir / "raw_notes" / f"{note_id}.json", record)
        return record

    def draft_cards_from_note(self, raw_note: dict[str, Any]) -> list[dict[str, Any]]:
        memo = str(raw_note.get("memo", ""))
        metadata = raw_note.get("metadata") if isinstance(raw_note.get("metadata"), dict) else {}
        cards: list[dict[str, Any]] = []
        for index, item in enumerate(_split_memo_items(memo), start=1):
            rule = _select_rule(item, self.config or {})
            knowledge_type = str(rule.get("knowledge_type", "lesson"))
            status = "needs_evidence" if knowledge_type == "domain_rule" else "unreviewed"
            card_id_prefix = "KR" if knowledge_type == "domain_rule" else "TK"
            card_id = f"{card_id_prefix}-{_date_prefix()}-D{index:03d}"
            categories = _ensure_list(rule.get("category"))
            workflow_stage = _ensure_list(rule.get("workflow_stage"))
            keywords = _ensure_list(rule.get("keywords"))
            card = {
                "id": card_id,
                "title": item[:48],
                "content": item,
                "knowledge_type": knowledge_type,
                "category": categories,
                "business_domain": _ensure_list(metadata.get("business_domain")),
                "ministry": _ensure_list(metadata.get("ministry")),
                "agency": _ensure_list(metadata.get("agency")),
                "business_type": _ensure_list(metadata.get("business_type")),
                "project_structure": _ensure_list(metadata.get("project_structure")),
                "workflow_stage": workflow_stage,
                "document_type": _ensure_list(metadata.get("document_type")),
                "trigger": {
                    "keywords": keywords,
                    "conditions": _ensure_list(rule.get("conditions")),
                    "negative_conditions": [],
                    "when_to_show": workflow_stage,
                },
                "recommended_action": _display_message(item, rule),
                "display": {
                    "surface_as": str(rule.get("surface_as", "checklist")),
                    "priority": str(rule.get("priority", "medium")),
                    "message": _display_message(item, rule),
                },
                "evidence": [
                    {
                        "source_type": str(metadata.get("source_type", "human_experience")),
                        "source_id": str(raw_note.get("id", "")),
                        "source_name": str(metadata.get("source_name", "사용자 메모")),
                        "page": None,
                        "section": None,
                        "quote": "",
                        "note": item,
                    }
                ],
                "verification": {
                    "status": status,
                    "reviewed_by": None,
                    "reviewed_at": None,
                    "confidence": "medium",
                },
                "relations": {
                    "related_announcements": [],
                    "related_regulations": [],
                    "related_knowledge_items": [],
                    "conflicts_with": [],
                    "supersedes": [],
                },
                "lifecycle": {
                    "created_at": _now(),
                    "updated_at": _now(),
                    "last_used_at": None,
                    "expires_at": None,
                },
            }
            cards.append(card)
        return cards

    def save_cards(self, cards: list[dict[str, Any]], *, confirm: bool = True) -> list[dict[str, Any]]:
        saved: list[dict[str, Any]] = []
        for card in cards:
            payload = dict(card)
            knowledge_type = str(payload.get("knowledge_type", "lesson"))
            directory_name = {
                "domain_rule": "rules",
                "announcement_fact": "facts",
                "inquiry_item": "inquiries",
            }.get(knowledge_type, "lessons")
            prefix = "KR" if knowledge_type == "domain_rule" else "KI"
            if not str(payload.get("id", "")).strip() or "-D" in str(payload.get("id", "")):
                payload["id"] = _next_id(self.root_dir / directory_name, prefix)
            verification = payload.get("verification") if isinstance(payload.get("verification"), dict) else {}
            if confirm:
                verification = dict(verification)
                verification["status"] = "confirmed"
                verification["reviewed_at"] = _now()
                verification["reviewed_by"] = verification.get("reviewed_by") or "user"
                payload["verification"] = verification
            lifecycle = payload.get("lifecycle") if isinstance(payload.get("lifecycle"), dict) else {}
            lifecycle = dict(lifecycle)
            lifecycle.setdefault("created_at", _now())
            lifecycle["updated_at"] = _now()
            payload["lifecycle"] = lifecycle
            _write_json(self.root_dir / directory_name / f"{payload['id']}.json", payload)
            self._append_relations_for_card(payload)
            saved.append(payload)
        return saved

    def state(self) -> dict[str, Any]:
        cards = self.list_cards()
        raw_notes = self._list_json_files(self.root_dir / "raw_notes")
        return {
            "store_path": str(self.root_dir),
            "raw_note_count": len(raw_notes),
            "card_count": len(cards),
            "cards": cards,
            "raw_notes": raw_notes[-20:],
            "relations": _read_json(self.root_dir / "relations.json", []),
        }

    def list_cards(self) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        for directory_name in ("lessons", "rules", "facts", "inquiries"):
            cards.extend(self._list_json_files(self.root_dir / directory_name))
        return sorted(cards, key=lambda item: str(item.get("lifecycle", {}).get("updated_at", "")), reverse=True)

    def _list_json_files(self, directory: Path) -> list[dict[str, Any]]:
        return [
            payload
            for payload in (_read_json(path, {}) for path in sorted(directory.glob("*.json")))
            if isinstance(payload, dict)
        ]

    def _append_relations_for_card(self, card: dict[str, Any]) -> None:
        card_id = str(card.get("id", ""))
        if not card_id:
            return
        relations = _read_json(self.root_dir / "relations.json", [])
        if not isinstance(relations, list):
            relations = []
        new_edges: list[dict[str, str]] = []
        for field, target_type in (
            ("business_domain", "business_domain"),
            ("ministry", "ministry"),
            ("agency", "agency"),
            ("workflow_stage", "workflow_stage"),
            ("category", "topic"),
        ):
            for value in _ensure_list(card.get(field)):
                new_edges.append(
                    {
                        "from_type": "knowledge_item",
                        "from_id": card_id,
                        "relation": "applies_to" if field != "category" else "triggered_by",
                        "to_type": target_type,
                        "to_id": value,
                    }
                )
        existing_keys = {
            (edge.get("from_id"), edge.get("relation"), edge.get("to_type"), edge.get("to_id"))
            for edge in relations
            if isinstance(edge, dict)
        }
        for edge in new_edges:
            key = (edge["from_id"], edge["relation"], edge["to_type"], edge["to_id"])
            if key not in existing_keys:
                relations.append(edge)
        _write_json(self.root_dir / "relations.json", relations)


def create_knowledge_draft(
    *,
    cwd: str | Path,
    memo: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = KnowledgeStore.for_project(cwd)
    raw_note = store.create_raw_note(memo, metadata or {})
    return {
        "raw_note": raw_note,
        "draft_cards": store.draft_cards_from_note(raw_note),
        "state": store.state(),
    }


def save_knowledge_cards(
    *,
    cwd: str | Path,
    cards: list[dict[str, Any]],
    confirm: bool = True,
) -> dict[str, Any]:
    store = KnowledgeStore.for_project(cwd)
    return {
        "saved_cards": store.save_cards(cards, confirm=confirm),
        "state": store.state(),
    }
