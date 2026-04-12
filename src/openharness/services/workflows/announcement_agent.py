"""Announcement agent filesystem and workbook generation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from openharness.services.workflows.agency_aliases import resolve_agency_label
from openharness.services.workflows.proposal_ops import build_proposal_ops_preview
from openharness.services.workflows.xlsx_writer import write_xlsx


SUMMARY_WORKBOOK_NAME = "총괄장.xlsx"
MONITORING_WORKBOOK_NAME = "공고_모니터링.xlsx"
MONITORING_JSON_NAME = "공고_모니터링.json"


@dataclass(frozen=True)
class AnnouncementAgentRequest:
    """Inputs for running the first announcement-agent automation pass."""

    file_name: str
    file_bytes: bytes
    structured_analysis: dict[str, Any]
    instruction: str = ""
    team_context: str = ""
    output_root: str | Path | None = None


def run_announcement_agent(request: AnnouncementAgentRequest) -> dict[str, Any]:
    """Create the first filesystem outputs for an analyzed announcement."""
    output_root = Path(
        request.output_root
        or os.environ.get("OPENHARNESS_PROPOSAL_OUTPUT_DIR", "")
        or Path.cwd() / ".openharness" / "proposal_outputs"
    ).expanduser()
    structured = request.structured_analysis
    overview = _as_dict(structured.get("announcement_overview"))
    schedule = _as_dict(structured.get("application_schedule"))
    title = str(overview.get("title") or Path(request.file_name).stem)
    deadline = _deadline_for_folder(schedule)
    agency = _agency_folder_label(structured)
    folder_name = _safe_path_segment(f"{deadline}-{agency}-{title}")
    project_dir = output_root / folder_name
    source_dir = project_dir / "00_공고_원문"
    source_dir.mkdir(parents=True, exist_ok=True)

    saved_source_path = source_dir / Path(request.file_name).name
    saved_source_path.write_bytes(request.file_bytes)

    proposal_ops = build_proposal_ops_preview(
        request=_proposal_ops_request(
            file_name=request.file_name,
            structured_analysis=structured,
            instruction=request.instruction,
            team_context=request.team_context,
        )
    )
    for folder in proposal_ops["folder_plan"]:
        (project_dir / Path(str(folder)).name).mkdir(parents=True, exist_ok=True)

    summary_workbook = project_dir / "99_관리로그" / SUMMARY_WORKBOOK_NAME
    write_xlsx(summary_workbook, _summary_workbook_sheets(structured, proposal_ops))

    monitoring_json = output_root / MONITORING_JSON_NAME
    monitoring_rows = _load_monitoring_rows(monitoring_json)
    row = _monitoring_row(request.file_name, structured)
    monitoring_rows = [existing for existing in monitoring_rows if existing["source_file"] != row["source_file"]]
    monitoring_rows.append(row)
    monitoring_json.parent.mkdir(parents=True, exist_ok=True)
    monitoring_json.write_text(
        json.dumps(monitoring_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    monitoring_workbook = output_root / MONITORING_WORKBOOK_NAME
    write_xlsx(monitoring_workbook, {"공고목록": _monitoring_sheet_rows(monitoring_rows)})

    return {
        "enabled": True,
        "output_root": str(output_root),
        "project_dir": str(project_dir),
        "folder_name": folder_name,
        "saved_source_files": [str(saved_source_path)],
        "summary_workbook": str(summary_workbook),
        "monitoring_workbook": str(monitoring_workbook),
        "monitoring_json": str(monitoring_json),
        "generated_files": [str(summary_workbook), str(monitoring_workbook)],
        "created_folders": [str(project_dir / Path(str(folder)).name) for folder in proposal_ops["folder_plan"]],
        "monitoring_row": row,
    }


def _proposal_ops_request(
    *,
    file_name: str,
    structured_analysis: dict[str, Any],
    instruction: str,
    team_context: str,
) -> Any:
    from openharness.services.workflows.proposal_ops import ProposalOpsRequest

    return ProposalOpsRequest(
        file_name=file_name,
        structured_analysis=structured_analysis,
        instruction=instruction,
        team_context=team_context,
    )


def _summary_workbook_sheets(
    structured: dict[str, Any], proposal_ops: dict[str, Any]
) -> dict[str, list[list[object]]]:
    overview = _as_dict(structured.get("announcement_overview"))
    budget = _as_dict(structured.get("budget"))
    schedule = _as_dict(structured.get("application_schedule"))
    channel = _as_dict(structured.get("submission_channel"))
    documents = _as_list(structured.get("submission_documents"))
    contacts = _as_list(structured.get("contacts"))
    consortium = _as_dict(structured.get("consortium_requirements"))

    return {
        "사업개요": [
            ["항목", "값"],
            ["사업명", overview.get("title", "")],
            ["사업목적", overview.get("main_purpose", "")],
            ["전체 과제수", ""],
            ["과제당 연구비", budget.get("total_amount", "")],
            ["총 연구기간", ""],
            ["당해연도 연구기간", ""],
        ],
        "문의처": _contacts_rows(contacts, proposal_ops),
        "접수": [
            ["항목", "값"],
            ["접수방법", channel.get("method", "")],
            ["접수처", channel.get("portal_or_address", "")],
            ["접수 마감일자", schedule.get("submission_deadline") or schedule.get("end_at") or ""],
        ],
        "제출서류": _submission_document_rows(documents),
        "컨소시엄": _consortium_rows(consortium),
    }


def _contacts_rows(contacts: list[Any], proposal_ops: dict[str, Any]) -> list[list[object]]:
    rows = [["구분", "기관", "담당자", "전화", "이메일", "주제"]]
    for contact in contacts:
        if not isinstance(contact, dict):
            continue
        rows.append(
            [
                "공고 문의처",
                contact.get("organization", ""),
                contact.get("name", ""),
                contact.get("phone", ""),
                contact.get("email", ""),
                contact.get("topic", ""),
            ]
        )
    rows.append([])
    rows.append(["전담기관 직접 확인 필요사항", "질문", "대상", "상태", "사유", ""])
    for question in proposal_ops.get("manager_questions", []):
        if isinstance(question, dict):
            rows.append(
                [
                    "확인필요",
                    question.get("question", ""),
                    question.get("target", ""),
                    question.get("status", ""),
                    question.get("reason", ""),
                    "",
                ]
            )
    return rows


def _submission_document_rows(documents: list[Any]) -> list[list[object]]:
    rows = [["제출서류", "주관", "공동", "위탁", "수요", "양식제공여부", "비고"]]
    for document in documents:
        if not isinstance(document, dict):
            continue
        required_for = {str(item).lower() for item in _as_list(document.get("required_for"))}
        rows.append(
            [
                document.get("document_name", ""),
                _mark(required_for, "주관", "lead"),
                _mark(required_for, "공동", "partner"),
                _mark(required_for, "위탁", "subcontractor"),
                _mark(required_for, "수요", "demand"),
                "O" if document.get("provided_form") else "",
                document.get("notes", ""),
            ]
        )
    if len(rows) == 1:
        rows.append(["제출서류 목록 확인 필요", "", "", "", "", "", "공고 분석에서 확정하지 못함"])
    return rows


def _consortium_rows(consortium: dict[str, Any]) -> list[list[object]]:
    rows = [
        ["항목", "공고상 구성요건", "후보기관", "담당자 메모"],
        ["컨소시엄 필수", _yes_no(consortium.get("consortium_required")), "", ""],
        ["수요기업 필수", _yes_no(consortium.get("demand_company_required")), "", ""],
        ["주관기관 가능", ", ".join(str(item) for item in _as_list(consortium.get("lead_org_allowed"))), "", ""],
        ["공동기관 가능", ", ".join(str(item) for item in _as_list(consortium.get("partner_org_allowed"))), "", ""],
        ["위탁 가능", _yes_no(consortium.get("subcontractor_allowed")), "", ""],
    ]
    for note in _as_list(consortium.get("notes")):
        rows.append(["비고", str(note), "", ""])
    return rows


def _monitoring_row(file_name: str, structured: dict[str, Any]) -> dict[str, str]:
    overview = _as_dict(structured.get("announcement_overview"))
    metadata = structured.get("metadata") if isinstance(structured.get("metadata"), dict) else {}
    schedule = _as_dict(structured.get("application_schedule"))
    budget = _as_dict(structured.get("budget"))
    return {
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_file": file_name,
        "ministry": str(metadata.get("ministry") or ""),
        "agency": _agency_folder_label(structured),
        "business_type": str(overview.get("project_type") or ""),
        "program_name": str(overview.get("title") or ""),
        "task_count": "",
        "budget_per_task_eok": str(budget.get("total_amount") or ""),
        "total_period": "",
        "current_year_budget_eok": "",
        "submission_deadline": str(schedule.get("submission_deadline") or schedule.get("end_at") or ""),
    }


def _monitoring_sheet_rows(rows: list[dict[str, str]]) -> list[list[object]]:
    headers = [
        "업로드한날짜",
        "부처",
        "전문기관",
        "사업구분",
        "사업명",
        "과제수",
        "과제당총 연구비(억원)",
        "전체연구기간",
        "이번연도 연구비(억원)",
        "접수마감일자",
        "원본파일",
    ]
    return [headers] + [
        [
            row["uploaded_at"],
            row["ministry"],
            row["agency"],
            row["business_type"],
            row["program_name"],
            row["task_count"],
            row["budget_per_task_eok"],
            row["total_period"],
            row["current_year_budget_eok"],
            row["submission_deadline"],
            row["source_file"],
        ]
        for row in rows
    ]


def _load_monitoring_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _deadline_for_folder(schedule: dict[str, Any]) -> str:
    raw = str(schedule.get("submission_deadline") or schedule.get("end_at") or "").strip()
    digits = "".join(char for char in raw if char.isdigit())
    return digits[2:8] if len(digits) >= 8 else "마감일확인"


def _agency_folder_label(structured: dict[str, Any]) -> str:
    metadata = structured.get("metadata") if isinstance(structured.get("metadata"), dict) else {}
    agency = str(
        metadata.get("agency")
        or metadata.get("professional_agency")
        or metadata.get("dedicated_agency")
        or metadata.get("ordering_agency")
        or metadata.get("client")
        or ""
    ).strip()
    if agency:
        return _safe_path_segment(resolve_agency_label(agency))
    return "기관확인"


def _mark(required_for: set[str], *candidates: str) -> str:
    return "O" if any(candidate.lower() in required_for for candidate in candidates) else ""


def _yes_no(value: Any) -> str:
    if value is True:
        return "O"
    if value is False:
        return "X"
    return ""


def _safe_path_segment(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char == "-" else "_" for char in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned[:120] or "untitled"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
