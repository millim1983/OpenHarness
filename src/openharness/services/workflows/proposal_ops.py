"""Proposal operations planning helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent.parent.parent.parent / "proposal_assets" / "config"

_FALLBACK_FOLDER_TEMPLATE = [
    "00_공고_원문",
    "01_기획_검토",
    "02_제안서_본문",
    "03_제출서류",
    "04_증빙_날인",
    "05_온라인접수",
    "99_관리로그",
]

_FALLBACK_ROLE_TASKS = [
    {
        "role": "사업관리",
        "owner": "Unassigned",
        "tasks": [
            "공고 기본정보와 제출 마감 확인",
            "제출서류 목록을 확정하고 담당자별 요청사항 발송",
            "온라인 접수 계정, 권한, 접수 경로 확인",
        ],
    },
]


@lru_cache(maxsize=1)
def _load_folder_template() -> list[str]:
    try:
        data = json.loads((_CONFIG_DIR / "folder_tree.json").read_text(encoding="utf-8"))
        folders = data.get("announcement_project_folders", [])
        if folders:
            return [str(f) for f in folders]
    except Exception as exc:
        logger.warning("folder_tree.json 로드 실패, fallback 사용: %s", exc)
    return _FALLBACK_FOLDER_TEMPLATE


@lru_cache(maxsize=1)
def _load_role_book() -> list[dict[str, Any]]:
    try:
        data = json.loads((_CONFIG_DIR / "role_book.json").read_text(encoding="utf-8"))
        roles = data.get("roles", [])
        if roles:
            return [
                {
                    "role": r.get("role", ""),
                    "label": r.get("label", r.get("role", "")),
                    "owner": r.get("default_owner", "Unassigned"),
                }
                for r in roles
                if isinstance(r, dict)
            ]
    except Exception as exc:
        logger.warning("role_book.json 로드 실패, fallback 사용: %s", exc)
    return []


@lru_cache(maxsize=1)
def _load_agency_aliases() -> dict[str, str]:
    try:
        data = json.loads((_CONFIG_DIR / "agency_aliases.json").read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception as exc:
        logger.warning("agency_aliases.json 로드 실패: %s", exc)
    return {}


@lru_cache(maxsize=1)
def _load_folder_rules() -> dict[str, Any]:
    try:
        data = json.loads((_CONFIG_DIR / "folder_rules.json").read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logger.warning("folder_rules.json 로드 실패: %s", exc)
    return {}


@dataclass(frozen=True)
class ProposalOpsRequest:
    """Inputs for creating an operations preview from one analyzed notice."""

    file_name: str
    structured_analysis: dict[str, Any]
    instruction: str = ""
    team_context: str = ""


def build_proposal_ops_preview(request: ProposalOpsRequest) -> dict[str, Any]:
    """Build a deterministic proposal-operations preview from analysis output."""
    structured = request.structured_analysis
    overview = _as_dict(structured.get("announcement_overview"))
    schedule = _as_dict(structured.get("application_schedule"))
    channel = _as_dict(structured.get("submission_channel"))
    risks = _as_dict(structured.get("risks_and_checks"))
    internal_plan = _as_dict(structured.get("internal_execution_plan"))
    documents = _as_list(structured.get("submission_documents"))
    knowledge_matches = _as_dict(structured.get("knowledge_matches"))

    title = str(overview.get("title") or request.file_name)
    deadline = str(schedule.get("submission_deadline") or schedule.get("end_at") or "")
    project_type = str(overview.get("project_type") or "")
    business_type = _guess_business_type(overview, structured)
    role_tasks = _build_role_tasks(internal_plan, request.team_context)
    submission_checklist = _build_submission_checklist(documents, channel, deadline)
    submission_checklist.extend(_knowledge_checklist_items(knowledge_matches))
    manager_questions = _build_manager_questions(risks, channel, deadline)
    manager_questions.extend(_knowledge_manager_questions(knowledge_matches))

    folder_template = _load_folder_template()
    folder_root = _build_folder_root(title, deadline, overview)
    folder_plan = [f"{folder_root}/{folder}" for folder in folder_template]
    # 로그 폴더와 접수 폴더는 folder_tree 기준으로 동적 탐색
    log_folder = next((f for f in folder_template if "관리" in f or "로그" in f), folder_template[-1])
    submit_folder = next((f for f in folder_template if "접수" in f), None)
    file_plan = [
        f"{folder_root}/{log_folder}/업무체크리스트.md",
        f"{folder_root}/{log_folder}/전담기관_문의사항.md",
        f"{folder_root}/{log_folder}/접수후_리포트.md",
    ]
    if submit_folder:
        file_plan.insert(2, f"{folder_root}/{submit_folder}/접수전_최종점검.md")

    return {
        "project_summary": {
            "title": title,
            "source_file": request.file_name,
            "project_type": project_type,
            "business_type": business_type,
            "submission_deadline": deadline,
            "submission_channel": str(channel.get("method") or channel.get("portal_or_address") or ""),
            "generated_from": "announcement_analysis",
        },
        "submission_checklist": submission_checklist,
        "manager_questions": manager_questions,
        "role_tasks": role_tasks,
        "reminder_plan": _build_reminder_plan(deadline),
        "folder_plan": folder_plan,
        "file_plan": file_plan,
        "execution_preview": _build_execution_preview(folder_template),
        "needs_manual_inputs": [
            "담당자 역할표",
            "제안접수 매뉴얼",
            "사업유형별 제출서류 규칙",
            "메시지 발송 채널과 담당자 연락처",
        ],
    }


def _build_submission_checklist(
    documents: list[Any], channel: dict[str, Any], deadline: str
) -> list[dict[str, str]]:
    checklist: list[dict[str, str]] = []
    if deadline:
        checklist.append(
            {
                "item": "제출 마감 재확인",
                "owner": "사업관리",
                "status": "needs_review",
                "basis": deadline,
            }
        )
    for document in documents:
        if not isinstance(document, dict):
            continue
        name = str(document.get("document_name") or "").strip()
        if not name:
            continue
        required_for = document.get("required_for")
        basis = ", ".join(str(item) for item in required_for) if isinstance(required_for, list) else ""
        checklist.append(
            {
                "item": name,
                "owner": "사업관리",
                "status": "needs_review",
                "basis": basis or str(document.get("notes") or ""),
            }
        )
    if channel:
        checklist.append(
            {
                "item": "온라인 접수 경로와 계정 권한 확인",
                "owner": "사업관리",
                "status": "needs_review",
                "basis": str(channel.get("portal_or_address") or channel.get("method") or ""),
            }
        )
    return checklist or [
        {
            "item": "제출서류 목록 수동 확인",
            "owner": "사업관리",
            "status": "needs_review",
            "basis": "분석 결과에서 제출서류를 확정하지 못했습니다.",
        }
    ]


def _knowledge_checklist_items(knowledge_matches: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for key in ("checklist", "warnings", "writing_guidance"):
        for match in _as_list(knowledge_matches.get(key)):
            if not isinstance(match, dict):
                continue
            message = str(match.get("message") or match.get("title") or "").strip()
            if not message:
                continue
            items.append(
                {
                    "item": message,
                    "owner": "사업관리",
                    "status": "needs_review",
                    "basis": str(match.get("reason") or match.get("knowledge_id") or "knowledge_match"),
                }
            )
    return items


def _knowledge_manager_questions(knowledge_matches: dict[str, Any]) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for match in _as_list(knowledge_matches.get("inquiry_items")):
        if not isinstance(match, dict):
            continue
        message = str(match.get("message") or match.get("title") or "").strip()
        if not message:
            continue
        questions.append(
            {
                "question": message,
                "target": "전담기관 또는 내부 검토자",
                "status": "open",
                "reason": str(match.get("knowledge_id") or "knowledge_match"),
            }
        )
    return questions


def _build_manager_questions(
    risks: dict[str, Any], channel: dict[str, Any], deadline: str
) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    for key in ("missing_information", "go_no_go_checks", "compliance_risks"):
        for item in _as_list(risks.get(key)):
            questions.append(
                {
                    "question": str(item),
                    "target": "전담기관 또는 내부 의사결정자",
                    "status": "open",
                    "reason": key,
                }
            )
    if not channel:
        questions.append(
            {
                "question": "온라인 접수 방식, 포털 주소, 계정 권한을 확인해야 합니다.",
                "target": "전담기관",
                "status": "open",
                "reason": "submission_channel_missing",
            }
        )
    if not deadline:
        questions.append(
            {
                "question": "제출 마감일과 마감 시간을 공식 경로로 재확인해야 합니다.",
                "target": "전담기관",
                "status": "open",
                "reason": "deadline_missing",
            }
        )
    return questions


def _build_folder_root(title: str, deadline: str, overview: dict[str, Any]) -> str:
    """folder_rules.json 패턴({deadline_yymmdd}-{agency_label}-{project_name})으로 루트 경로 생성."""
    rules = _load_folder_rules()
    aliases = _load_agency_aliases()

    # deadline → yymmdd 변환
    deadline_label = rules.get("unknown_deadline_label", "마감일확인")
    if deadline:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y년 %m월 %d일"):
            try:
                dt = datetime.strptime(deadline[:10], fmt[:len(fmt)])
                deadline_label = dt.strftime("%y%m%d")
                break
            except ValueError:
                continue

    # agency 추출 → alias 변환
    agency_fields = rules.get("agency_source_fields", ["agency", "professional_agency", "dedicated_agency", "ordering_agency", "client"])
    raw_agency = ""
    for field in agency_fields:
        val = str(overview.get(field) or "").strip()
        if val:
            raw_agency = val
            break
    agency_label = aliases.get(raw_agency, "") or _safe_path_segment(raw_agency) or rules.get("unknown_agency_label", "기관확인")

    project_name = _safe_path_segment(title)
    return f"{deadline_label}-{agency_label}-{project_name}"


def _build_execution_preview(folder_template: list[str]) -> list[str]:
    announce_folder = next((f for f in folder_template if "공고" in f), folder_template[0] if folder_template else "공고")
    doc_folder = next((f for f in folder_template if "제출" in f or "서류" in f), None)
    log_folder = next((f for f in folder_template if "관리" in f or "로그" in f), folder_template[-1] if folder_template else "관리로그")
    lines = [
        "사용자 승인 전에는 실제 폴더 생성, 파일 이동, 메시지 발송을 하지 않습니다.",
        f"승인 후 공고 원문 파일을 {announce_folder} 하위로 정리합니다.",
    ]
    if doc_folder:
        lines.append(f"승인 후 제출양식 파일을 {doc_folder} 하위로 정리합니다.")
    lines += [
        f"승인 후 업무체크리스트, 전담기관 문의사항, 접수전 최종점검 파일을 {log_folder} 하위에 생성합니다.",
        "담당자별 체크리스트와 리마인드는 메시지 채널이 연결된 뒤 예약합니다.",
    ]
    return lines


def _build_role_tasks(internal_plan: dict[str, Any], team_context: str) -> list[dict[str, Any]]:
    # 1순위: 공고 분석에서 추출한 team_assignments
    assignments = _as_list(internal_plan.get("team_assignments"))
    if assignments:
        role_tasks: list[dict[str, Any]] = []
        for item in assignments:
            if not isinstance(item, dict):
                continue
            role_tasks.append(
                {
                    "role": str(item.get("team_member") or "Unassigned"),
                    "owner": str(item.get("team_member") or "Unassigned"),
                    "tasks": [str(item.get("responsibility") or "담당 업무 확인")],
                    "manager_plus_one": "담당자 역할표 업로드 후 보강 필요",
                }
            )
        if role_tasks:
            return role_tasks

    # 2순위: team_context 힌트
    if team_context.strip():
        return [
            {
                "role": "팀 컨텍스트 기반 배정",
                "owner": "사업관리",
                "tasks": ["업로드된 팀 컨텍스트를 기준으로 역할표를 확정해야 합니다."],
                "manager_plus_one": "역할표 업로드 후 보강 필요",
            }
        ]

    # 3순위: role_book.json (config) → fallback
    role_book = _load_role_book()
    if role_book:
        return [
            {
                "role": r["role"],
                "label": r["label"],
                "owner": r["owner"],
                "tasks": ["담당 업무를 확정해야 합니다."],
            }
            for r in role_book
        ]
    return _FALLBACK_ROLE_TASKS


def _build_reminder_plan(deadline: str) -> list[dict[str, str]]:
    return [
        {
            "phase": "normal",
            "cadence": "매일 1회",
            "target": "미완료 담당자",
            "condition": "마감 4일 전까지",
        },
        {
            "phase": "deadline_watch",
            "cadence": "오전/오후 2회",
            "target": "미완료 담당자 및 사업관리",
            "condition": f"마감 3일 전부터 {deadline or '제출 마감'}까지",
        },
    ]


def _guess_business_type(overview: dict[str, Any], structured: dict[str, Any]) -> str:
    haystack = " ".join(
        str(value)
        for value in [
            overview.get("title"),
            overview.get("project_type"),
            overview.get("main_purpose"),
            overview.get("support_summary"),
            structured,
        ]
    )
    if "용역" in haystack:
        return "service_contract"
    if "R&D" in haystack or "연구" in haystack or "개발" in haystack:
        return "rd"
    if "지원" in haystack or "보조" in haystack:
        return "support_program"
    return "unknown"


def _safe_path_segment(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:80] or "untitled"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
