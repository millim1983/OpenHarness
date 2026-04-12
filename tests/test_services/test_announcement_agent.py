from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from openharness.services.workflows.announcement_agent import (
    AnnouncementAgentRequest,
    run_announcement_agent,
)


def test_run_announcement_agent_creates_project_folder_and_workbooks(tmp_path: Path) -> None:
    result = run_announcement_agent(
        AnnouncementAgentRequest(
            file_name="notice.pdf",
            file_bytes=b"pdf bytes",
            output_root=tmp_path,
            structured_analysis={
                "metadata": {"agency": "KIAT", "ministry": "MOTIE"},
                "announcement_overview": {
                    "title": "AI Product Support",
                    "main_purpose": "Commercialization",
                    "project_type": "R&D",
                },
                "application_schedule": {"submission_deadline": "2026-05-01 18:00"},
                "submission_channel": {
                    "method": "online",
                    "portal_or_address": "example.go.kr",
                },
                "budget": {"total_amount": "5억원"},
                "contacts": [{"organization": "KIAT", "phone": "02-0000-0000"}],
                "submission_documents": [
                    {
                        "document_name": "신청서",
                        "required_for": ["lead", "partner"],
                        "provided_form": True,
                    }
                ],
                "consortium_requirements": {
                    "consortium_required": True,
                    "demand_company_required": False,
                    "lead_org_allowed": ["기업"],
                    "partner_org_allowed": ["대학"],
                },
                "risks_and_checks": {"missing_information": ["계정 권한 확인"]},
            },
        )
    )

    project_dir = Path(result["project_dir"])
    assert project_dir.exists()
    assert Path(result["saved_source_files"][0]).read_bytes() == b"pdf bytes"
    assert Path(result["summary_workbook"]).exists()
    assert Path(result["monitoring_workbook"]).exists()
    assert Path(result["monitoring_json"]).exists()

    with ZipFile(result["summary_workbook"]) as workbook:
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
        assert "xl/worksheets/sheet5.xml" in workbook.namelist()
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        assert "사업개요" in workbook_xml
        assert "제출서류" in workbook_xml
