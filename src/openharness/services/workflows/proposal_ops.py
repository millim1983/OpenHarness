"""Proposal operations planning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


DEFAULT_FOLDER_TEMPLATE = [
    "00_공고_원문",
    "01_기획_검토",
    "02_제안서_본문",
    "03_제출서류",
    "04_증빙_날인",
    "05_온라인접수",
    "99_관리로그",
]

DEFAULT_ROLE_TASKS = [
    {
        "role": "사업관리",
        "owner": "Unassigned",
        "tasks": [
            "공고 기본정보와 제출 마감 확인",
            "제출서류 목록을 확정하고 담당자별 요청사항 발송",
            "온라인 접수 계정, 권한, 접수 경로 확인",
        ],
    },
    {
        "role": "제안서 본문",
        "owner": "Unassigned",
        "tasks": [
            "제안서 본문 작성 범위와 마감 일정 확인",
            "본문 작성에 필요한 공고 요구사항 확인",
        ],
    },
    {
        "role": "대표/의사결정",
        "owner": "Unassigned",
        "tasks": [
            "참여 여부와 핵심 전략 확인",
            "전담기관 문의 필요사항 검토",
        ],
    },
]


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

    title = str(overview.get("title") or request.file_name)
    deadline = str(schedule.get("submission_deadline") or schedule.get("end_at") or "")
    project_type = str(overview.get("project_type") or "")
    business_type = _guess_business_type(overview, structured)
    role_tasks = _build_role_tasks(internal_plan, request.team_context)
    submission_checklist = _build_submission_checklist(documents, channel, deadline)
    manager_questions = _build_manager_questions(risks, channel, deadline)

    safe_title = _safe_path_segment(title)
    folder_root = f"proposal_ops/{datetime.now().year}_{safe_title}"
    folder_plan = [f"{folder_root}/{folder}" for folder in DEFAULT_FOLDER_TEMPLATE]
    file_plan = [
        f"{folder_root}/99_관리로그/업무체크리스트.md",
        f"{folder_root}/99_관리로그/전담기관_문의사항.md",
        f"{folder_root}/05_온라인접수/접수전_최종점검.md",
        f"{folder_root}/99_관리로그/접수후_리포트.md",
    ]

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
        "execution_preview": [
            "사용자 승인 전에는 실제 폴더 생성, 파일 이동, 메시지 발송을 하지 않습니다.",
            "승인 후 공고와 제출양식 파일을 00_공고_원문 및 03_제출서류 하위로 정리합니다.",
            "승인 후 업무체크리스트, 전담기관 문의사항, 접수전 최종점검 파일을 생성합니다.",
            "담당자별 체크리스트와 리마인드는 메시지 채널이 연결된 뒤 예약합니다.",
        ],
        "needs_manual_inputs": [
            "담당자 역할표",
            "제안접수 매뉴얼",
            "사업유형별 제출서류 규칙",
            "폴더/파일명 규칙",
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


def _build_role_tasks(internal_plan: dict[str, Any], team_context: str) -> list[dict[str, Any]]:
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
    if team_context.strip():
        return [
            {
                "role": "팀 컨텍스트 기반 배정",
                "owner": "사업관리",
                "tasks": ["업로드된 팀 컨텍스트를 기준으로 역할표를 확정해야 합니다."],
                "manager_plus_one": "역할표 업로드 후 보강 필요",
            }
        ]
    return DEFAULT_ROLE_TASKS


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
