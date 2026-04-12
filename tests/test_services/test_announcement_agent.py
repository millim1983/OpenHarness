from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from openharness.services.workflows.announcement_agent import (
    AnnouncementAgentRequest,
    AnnouncementSourceFile,
    run_announcement_agent,
)


def test_run_announcement_agent_creates_project_folder_and_workbooks(tmp_path: Path) -> None:
    result = run_announcement_agent(
        AnnouncementAgentRequest(
            file_name="notice.pdf",
            file_bytes=b"pdf bytes",
            output_root=tmp_path,
            structured_analysis={
                "metadata": {"agency": "한국산업기술진흥원", "ministry": "MOTIE"},
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
    assert result["folder_name"].startswith("260501-KIAT-AI_Product_Support")
    assert result["monitoring_row"]["agency"] == "KIAT"
    assert result["monitoring_row"]["business_domain"] == "Commercialization"
    assert Path(result["saved_source_files"][0]).read_bytes() == b"pdf bytes"
    assert Path(result["summary_workbook"]).exists()
    assert Path(result["summary_workbook"]).parent == project_dir
    assert Path(result["attachment_manifest"]).exists()
    assert Path(result["monitoring_workbook"]).exists()
    assert Path(result["monitoring_workbook"]).name.startswith("공고리스트_")
    assert Path(result["monitoring_json"]).exists()
    assert result["created_folders"] == [str(project_dir)]
    assert result["dashboard_stats"]["total_count"] == 1
    assert result["dashboard_stats"]["by_business_domain"] == {"Commercialization": 1}

    with ZipFile(result["summary_workbook"]) as workbook:
        assert "xl/worksheets/sheet1.xml" in workbook.namelist()
        assert "xl/worksheets/sheet5.xml" in workbook.namelist()
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        assert "사업개요" in workbook_xml
        assert "제출서류" in workbook_xml


def test_run_announcement_agent_uses_full_agency_name_when_alias_missing(
    tmp_path: Path,
) -> None:
    result = run_announcement_agent(
        AnnouncementAgentRequest(
            file_name="notice.pdf",
            file_bytes=b"pdf bytes",
            output_root=tmp_path,
            structured_analysis={
                "metadata": {"ordering_agency": "서울특별시"},
                "announcement_overview": {"title": "Smart City SI"},
                "application_schedule": {"submission_deadline": "2026.06.02 15:00"},
            },
        )
    )

    assert result["folder_name"].startswith("260602-서울특별시-Smart_City_SI")
    assert result["monitoring_row"]["agency"] == "서울특별시"


def test_run_announcement_agent_saves_uploaded_file_set_without_proposal_tree(
    tmp_path: Path,
) -> None:
    result = run_announcement_agent(
        AnnouncementAgentRequest(
            file_name="notice.pdf",
            file_bytes=b"pdf bytes",
            output_root=tmp_path,
            source_files=[
                AnnouncementSourceFile(
                    file_name="notice.pdf",
                    file_bytes=b"notice bytes",
                    relative_path="upload_set/notice.pdf",
                ),
                AnnouncementSourceFile(
                    file_name="form.xlsx",
                    file_bytes=b"form bytes",
                    relative_path="upload_set/forms/form.xlsx",
                ),
            ],
            structured_analysis={
                "metadata": {"agency": "정보통신기획평가원", "ministry": "MSIT"},
                "announcement_overview": {"title": "AI Platform", "project_type": "R&D"},
                "application_schedule": {"submission_deadline": "2026-07-03 18:00"},
            },
        )
    )

    project_dir = Path(result["project_dir"])

    assert (project_dir / "upload_set" / "notice.pdf").read_bytes() == b"notice bytes"
    assert (project_dir / "upload_set" / "forms" / "form.xlsx").read_bytes() == b"form bytes"
    assert not (project_dir / "01.공고 및 양식").exists()
    assert not (project_dir / "99.휴지통").exists()
    attachment_manifest = json.loads(
        Path(result["attachment_manifest"]).read_text(encoding="utf-8")
    )
    assert attachment_manifest[0]["role"] == "notice_pdf"
    assert attachment_manifest[1]["role"] == "attachment"
    assert attachment_manifest[1]["indexed"] is False
    assert Path(result["summary_workbook"]).parent == project_dir
    assert len(result["saved_source_files"]) == 2


def test_run_announcement_agent_can_be_disabled(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "feature_flags.json").write_text(
        '{"announcement_agent": false}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENHARNESS_PROPOSAL_CONFIG_DIR", str(config_dir))

    result = run_announcement_agent(
        AnnouncementAgentRequest(
            file_name="notice.pdf",
            file_bytes=b"pdf bytes",
            output_root=tmp_path,
            structured_analysis={},
        )
    )

    assert result["enabled"] is False
    assert not (tmp_path / "notice.pdf").exists()
