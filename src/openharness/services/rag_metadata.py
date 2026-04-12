"""Layered metadata helpers for project-local RAG documents."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


RAG_METADATA_SCHEMA_VERSION = 1
DocumentType = Literal["announcement", "regulation", "technical", "company_team", "unknown"]


@dataclass(frozen=True)
class CommonRagMetadata:
    """Fields shared by every indexed document."""

    document_type: DocumentType
    title: str
    source_file: str
    content_hash: str = ""
    uploaded_at: str = ""
    embedding_profile: str = ""
    chunk_count: int = 0
    tags: list[str] = field(default_factory=list)
    language: str = "unknown"
    source_kind: str = "upload"


@dataclass(frozen=True)
class AnnouncementMetadata:
    ministry: str = ""
    agency: str = ""
    business_type: str = ""
    rd_or_non_rd: str = ""
    program_name: str = ""
    submission_channel: str = ""
    submission_deadline: str = ""
    contacts: list[dict[str, str]] = field(default_factory=list)
    related_regulations: list[str] = field(default_factory=list)
    eligibility_roles: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RegulationMetadata:
    regulation_owner: str = ""
    applies_to_business_type: str = ""
    effective_date: str = ""
    article_scope: str = ""
    related_ministry: str = ""
    related_agency: str = ""


@dataclass(frozen=True)
class TechnicalDocumentMetadata:
    technology_domain: str = ""
    product_or_system: str = ""
    version: str = ""
    spec_scope: str = ""
    related_project_or_program: str = ""


@dataclass(frozen=True)
class CompanyTeamMetadata:
    department: str = ""
    owner: str = ""
    responsibility_area: str = ""
    related_task: str = ""


@dataclass(frozen=True)
class RagDocumentMetadata:
    """Complete layered metadata payload for one indexed document."""

    common: CommonRagMetadata
    announcement: AnnouncementMetadata | None = None
    regulation: RegulationMetadata | None = None
    technical: TechnicalDocumentMetadata | None = None
    company_team: CompanyTeamMetadata | None = None
    chat_profile: str = ""
    instruction: str = ""
    has_team_context: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "metadata_schema_version": RAG_METADATA_SCHEMA_VERSION,
            **asdict(self.common),
            "chat_profile": self.chat_profile,
            "instruction": self.instruction,
            "has_team_context": self.has_team_context,
        }
        if self.announcement is not None:
            announcement = asdict(self.announcement)
            payload["announcement"] = announcement
            payload.update(
                {
                    "ministry": announcement["ministry"],
                    "agency": announcement["agency"],
                    "business_type": announcement["business_type"],
                    "rd_or_non_rd": announcement["rd_or_non_rd"],
                    "submission_deadline": announcement["submission_deadline"],
                }
            )
        if self.regulation is not None:
            payload["regulation"] = asdict(self.regulation)
        if self.technical is not None:
            payload["technical"] = asdict(self.technical)
        if self.company_team is not None:
            payload["company_team"] = asdict(self.company_team)
        return payload


def build_rag_document_metadata(
    *,
    file_name: str,
    extracted_text: str,
    embedding_profile: str = "",
    chat_profile: str = "",
    instruction: str = "",
    has_team_context: bool = False,
    source_kind: str = "web_mvp_upload",
    structured_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify and extract layered metadata for an indexed document."""

    analysis = structured_analysis or {}
    document_type = classify_document_type(file_name, extracted_text, analysis)
    title = _extract_title(file_name, extracted_text, analysis)
    common = CommonRagMetadata(
        document_type=document_type,
        title=title,
        source_file=file_name,
        uploaded_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        embedding_profile=embedding_profile,
        tags=_metadata_tags(document_type, analysis),
        language=_detect_language(extracted_text),
        source_kind=source_kind,
    )
    metadata = RagDocumentMetadata(
        common=common,
        announcement=_extract_announcement_metadata(analysis, extracted_text)
        if document_type == "announcement"
        else None,
        regulation=_extract_regulation_metadata(extracted_text)
        if document_type == "regulation"
        else None,
        technical=_extract_technical_metadata(extracted_text)
        if document_type == "technical"
        else None,
        company_team=_extract_company_team_metadata(extracted_text)
        if document_type == "company_team"
        else None,
        chat_profile=chat_profile,
        instruction=instruction,
        has_team_context=has_team_context,
    ).to_dict()
    return _drop_empty_nested(metadata)


def enrich_metadata_for_index(
    metadata: dict[str, Any] | None,
    *,
    content_hash: str,
    chunk_count: int,
) -> dict[str, Any]:
    """Add indexer-known fields without requiring callers to know them."""

    payload = dict(metadata or {})
    payload.setdefault("metadata_schema_version", RAG_METADATA_SCHEMA_VERSION)
    payload.setdefault("document_type", "unknown")
    payload["content_hash"] = content_hash
    payload["chunk_count"] = chunk_count
    return payload


def classify_document_type(
    file_name: str,
    extracted_text: str,
    structured_analysis: dict[str, Any] | None = None,
) -> DocumentType:
    """Classify a document before type-specific metadata extraction."""

    analysis = structured_analysis or {}
    if _has_announcement_analysis(analysis):
        return "announcement"

    text = f"{file_name}\n{extracted_text[:8000]}".lower()
    if _matches_any(
        text,
        "공고",
        "모집",
        "지원사업",
        "사업계획서",
        "신청기간",
        "제출기한",
        "funding notice",
        "call for proposals",
        "application deadline",
    ):
        return "announcement"
    if _matches_any(text, "규정", "지침", "운영요령", "article ", "effective date", "regulation"):
        return "regulation"
    if _matches_any(text, "api", "specification", "architecture", "version", "requirements", "sdk"):
        return "technical"
    if _matches_any(text, "department", "owner", "responsibility", "team", "담당", "부서", "업무분장"):
        return "company_team"
    return "unknown"


def _extract_announcement_metadata(
    analysis: dict[str, Any], extracted_text: str
) -> AnnouncementMetadata:
    overview = _dict_value(analysis.get("announcement_overview"))
    schedule = _dict_value(analysis.get("application_schedule"))
    channel = _dict_value(analysis.get("submission_channel"))
    contacts = _contact_items(analysis.get("contacts"))
    eligibility = _eligibility_roles(analysis.get("eligibility_by_role"))
    agency, ministry = _agency_and_ministry(contacts, extracted_text)
    return AnnouncementMetadata(
        ministry=ministry,
        agency=agency,
        business_type=_string_value(overview, "project_type"),
        rd_or_non_rd=_infer_rd_or_non_rd(extracted_text),
        program_name=_string_value(overview, "title"),
        submission_channel=_join_non_empty(
            _string_value(channel, "method"),
            _string_value(channel, "portal_or_address"),
        ),
        submission_deadline=_string_value(schedule, "submission_deadline")
        or _string_value(schedule, "end_at"),
        contacts=contacts,
        related_regulations=_related_regulations(extracted_text),
        eligibility_roles=eligibility,
    )


def _extract_regulation_metadata(extracted_text: str) -> RegulationMetadata:
    return RegulationMetadata(
        regulation_owner=_first_labeled_value(extracted_text, "owner", "소관", "담당부서"),
        applies_to_business_type=_first_labeled_value(extracted_text, "applies to", "적용대상"),
        effective_date=_first_labeled_value(extracted_text, "effective date", "시행일"),
        article_scope=_first_labeled_value(extracted_text, "scope", "목적", "적용범위"),
        related_ministry=_first_match(extracted_text, r"[\w가-힣]+부"),
        related_agency=_first_match(extracted_text, r"[\w가-힣]+청"),
    )


def _extract_technical_metadata(extracted_text: str) -> TechnicalDocumentMetadata:
    return TechnicalDocumentMetadata(
        technology_domain=_first_labeled_value(extracted_text, "domain", "technology", "기술분야"),
        product_or_system=_first_labeled_value(extracted_text, "system", "product", "시스템"),
        version=_first_labeled_value(extracted_text, "version", "버전"),
        spec_scope=_first_labeled_value(extracted_text, "scope", "spec scope", "범위"),
        related_project_or_program=_first_labeled_value(
            extracted_text,
            "project",
            "program",
            "프로젝트",
        ),
    )


def _extract_company_team_metadata(extracted_text: str) -> CompanyTeamMetadata:
    return CompanyTeamMetadata(
        department=_first_labeled_value(extracted_text, "department", "부서"),
        owner=_first_labeled_value(extracted_text, "owner", "담당자"),
        responsibility_area=_first_labeled_value(extracted_text, "responsibility", "담당업무"),
        related_task=_first_labeled_value(extracted_text, "task", "업무", "과제"),
    )


def _has_announcement_analysis(analysis: dict[str, Any]) -> bool:
    overview = _dict_value(analysis.get("announcement_overview"))
    schedule = _dict_value(analysis.get("application_schedule"))
    channel = _dict_value(analysis.get("submission_channel"))
    return any(
        (
            _string_value(overview, "title"),
            _string_value(overview, "project_type"),
            _string_value(schedule, "submission_deadline"),
            _string_value(channel, "method"),
        )
    )


def _extract_title(file_name: str, extracted_text: str, analysis: dict[str, Any]) -> str:
    overview = _dict_value(analysis.get("announcement_overview"))
    title = _string_value(overview, "title")
    if title:
        return title
    for line in extracted_text.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate[:160]
    return file_name


def _metadata_tags(document_type: DocumentType, analysis: dict[str, Any]) -> list[str]:
    tags = [document_type]
    overview = _dict_value(analysis.get("announcement_overview"))
    project_type = _string_value(overview, "project_type")
    if project_type:
        tags.append(project_type)
    return tags


def _detect_language(text: str) -> str:
    sample = text[:4000]
    has_korean = any("가" <= char <= "힣" for char in sample)
    has_ascii_letters = any(("a" <= char.lower() <= "z") for char in sample)
    if has_korean and has_ascii_letters:
        return "mixed"
    if has_korean:
        return "ko"
    if has_ascii_letters:
        return "en"
    return "unknown"


def _dict_value(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_value(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def _join_non_empty(*values: str) -> str:
    return " ".join(value for value in values if value).strip()


def _contact_items(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    contacts: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        contacts.append(
            {
                "organization": _string_value(item, "organization"),
                "name": _string_value(item, "name"),
                "phone": _string_value(item, "phone"),
                "email": _string_value(item, "email"),
                "topic": _string_value(item, "topic"),
            }
        )
    return contacts


def _eligibility_roles(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    roles: list[str] = []
    for item in value:
        if isinstance(item, dict):
            role = _string_value(item, "role")
            if role:
                roles.append(role)
    return roles


def _agency_and_ministry(contacts: list[dict[str, str]], extracted_text: str) -> tuple[str, str]:
    organizations = [contact["organization"] for contact in contacts if contact.get("organization")]
    ministry = next((org for org in organizations if "Ministry" in org or org.endswith("부")), "")
    agency = next((org for org in organizations if org != ministry), "")
    if not ministry:
        ministry = _first_labeled_value(
            extracted_text,
            "ministry",
            "주관부처",
            "소관부처",
            "담당부처",
        )
    if not ministry:
        ministry = _first_match(extracted_text, r"[\w가-힣]+부")
    if not agency:
        agency = _first_labeled_value(
            extracted_text,
            "agency",
            "전담기관",
            "전문기관",
            "발주처",
            "사업담당부서",
            "수행기관",
            "주관기관",
        )
    if not agency:
        agency = _first_match(extracted_text, r"[\w가-힣]+청|[\w가-힣]+진흥원|[\w가-힣]+공단")
    return agency, ministry


def _infer_rd_or_non_rd(extracted_text: str) -> str:
    lowered = extracted_text.lower()
    if "비r&d" in lowered or "non-r&d" in lowered or "사업화" in extracted_text:
        return "non_rd"
    if "r&d" in lowered or "research and development" in lowered or "연구개발" in extracted_text:
        return "rd"
    return ""


def _related_regulations(extracted_text: str) -> list[str]:
    matches = re.findall(r"([가-힣A-Za-z0-9 ]+(?:규정|지침|법|령|요령))", extracted_text)
    return [match.strip() for match in matches[:5] if match.strip()]


def _first_labeled_value(text: str, *labels: str) -> str:
    for label in labels:
        pattern = rf"(?im)^\s*{re.escape(label)}\s*[:：]\s*(.+?)\s*$"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()[:160]
    return ""


def _first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text)
    return match.group(0).strip() if match else ""


def _matches_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _drop_empty_nested(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            cleaned[key] = {
                nested_key: nested_value
                for nested_key, nested_value in value.items()
                if nested_value not in ("", [], {}, None)
            }
            continue
        cleaned[key] = value
    return cleaned
