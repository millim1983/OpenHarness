from __future__ import annotations

import io
import zipfile

import pytest

from openharness.services.document_processing import (
    build_document_analysis_prompt,
    extract_text_from_document,
    format_document_analysis_summary,
    parse_document_analysis_response,
)


def test_extract_text_from_utf8_text_file() -> None:
    text = extract_text_from_document("notes.txt", "alpha\nbeta".encode("utf-8"))

    assert text == "alpha\nbeta"


def test_extract_text_from_docx_file() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body>"
                "<w:p><w:r><w:t>Quarterly review</w:t></w:r></w:p>"
                "<w:p><w:r><w:t>Revenue up 14 percent</w:t></w:r></w:p>"
                "</w:body>"
                "</w:document>"
            ),
        )

    text = extract_text_from_document("report.docx", buffer.getvalue())

    assert text == "Quarterly review\nRevenue up 14 percent"


def test_extract_text_rejects_unknown_binary_file() -> None:
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text_from_document("archive.bin", b"\x00\xff\x00\xff")


def test_build_document_analysis_prompt_never_truncates() -> None:
    long_text = "x" * 100_000
    prompt, truncated = build_document_analysis_prompt(
        "roadmap.txt",
        long_text,
        "Focus on owners and deadlines.",
        "Alex PM: schedule management, final submission",
    )

    assert truncated is False
    assert "Return only valid JSON" in prompt
    assert "Focus on owners and deadlines." in prompt
    assert "Alex PM: schedule management, final submission" in prompt
    assert long_text in prompt


def test_parse_document_analysis_response_normalizes_missing_fields() -> None:
    parsed = parse_document_analysis_response(
        """
        {
          "announcement_overview": {
            "title": "AI Commercialization Program",
            "main_purpose": "Plan launch work",
            "project_type": "Type 1",
            "support_summary": "Prototype and certification support"
          },
          "consortium_requirements": {
            "consortium_required": true,
            "demand_company_required": true,
            "lead_org_allowed": ["SME"],
            "partner_org_allowed": ["University"],
            "subcontractor_allowed": false,
            "notes": ["Demand company is mandatory"]
          },
          "eligibility_by_role": [
            {
              "role": "Lead organization",
              "eligible_entities": ["SME"],
              "restrictions": ["Domestic corporation only"]
            }
          ],
          "recommended_consortium_strategy": {
            "recommended_structure": ["Lead org + demand company + university"],
            "recommended_role_rr": [
              {
                "role": "Lead organization",
                "recommended_entity_type": "Company",
                "responsibilities": ["Overall management", "Final submission"]
              }
            ],
            "key_differentiators": ["Secure a validation partner early"]
          },
          "budget": {
            "total_amount": "KRW 400M",
            "by_year": [{"year": "Year 1", "amount": "KRW 200M"}],
            "matching_requirement": "30 percent or more",
            "additional_info_needed": ["Detailed cost table required"]
          },
          "submission_documents": [
            {
              "document_name": "Project proposal",
              "required_for": ["Lead organization"],
              "provided_form": true,
              "issuance_source": "Template provided",
              "notes": "Signature required"
            }
          ],
          "presentation": {"required": true, "notes": "Presentation review expected"},
          "application_schedule": {
            "announcement_date": "2026-03-19",
            "start_at": "2026-03-26",
            "end_at": "2026-04-17 18:00",
            "submission_deadline": "2026-04-17 18:00",
            "important_milestones": [{"date": "2026-04-17 18:00", "label": "Final deadline"}]
          },
          "submission_channel": {
            "method": "Online",
            "portal_or_address": "Funding portal",
            "notes": "File upload required"
          },
          "contacts": [
            {
              "organization": "Program office",
              "name": "Jordan Kim",
              "phone": "02-0000-0000",
              "email": "help@example.com",
              "topic": "Announcement inquiry"
            }
          ],
          "risks_and_checks": {
            "compliance_risks": ["Eligibility mismatch"],
            "missing_information": ["Detailed cost table missing"],
            "go_no_go_checks": ["Demand company secured"]
          },
          "internal_execution_plan": {
            "team_assignments": [
              {
                "team_member": "Alex PM",
                "responsibility": "Submission lead",
                "reason": "Owns schedule coordination"
              }
            ],
            "immediate_next_actions": ["Secure demand company", "Prepare submission checklist"]
          }
        }
        """
    )

    assert parsed["announcement_overview"]["main_purpose"] == "Plan launch work"
    assert parsed["consortium_requirements"]["consortium_required"] is True
    assert parsed["eligibility_by_role"][0]["role"] == "Lead organization"
    assert parsed["recommended_consortium_strategy"]["recommended_role_rr"][0]["recommended_entity_type"] == "Company"
    assert parsed["budget"]["by_year"][0]["amount"] == "KRW 200M"
    assert parsed["submission_documents"][0]["provided_form"] is True
    assert parsed["presentation"]["required"] is True
    assert parsed["application_schedule"]["submission_deadline"] == "2026-04-17 18:00"
    assert parsed["submission_channel"]["method"] == "Online"
    assert parsed["contacts"][0]["name"] == "Jordan Kim"
    assert parsed["risks_and_checks"]["compliance_risks"] == ["Eligibility mismatch"]
    assert parsed["internal_execution_plan"]["team_assignments"][0]["team_member"] == "Alex PM"


def test_parse_document_analysis_response_rejects_invalid_json() -> None:
    with pytest.raises(ValueError, match="did not return valid JSON"):
        parse_document_analysis_response("not json")


def test_parse_document_analysis_response_accepts_json_code_fence() -> None:
    parsed = parse_document_analysis_response(
        """```json
        {
          "announcement_overview": {
            "title": "Review a contract",
            "main_purpose": "Review a contract",
            "project_type": "",
            "support_summary": ""
          },
          "consortium_requirements": {},
          "eligibility_by_role": [],
          "recommended_consortium_strategy": {},
          "budget": {},
          "submission_documents": [],
          "presentation": {},
          "application_schedule": {},
          "submission_channel": {},
          "contacts": [],
          "risks_and_checks": {"compliance_risks": ["Clause ambiguity"]},
          "internal_execution_plan": {}
        }
        ```"""
    )

    assert parsed["announcement_overview"]["main_purpose"] == "Review a contract"
    assert parsed["risks_and_checks"]["compliance_risks"] == ["Clause ambiguity"]


def test_parse_document_analysis_response_accepts_wrapped_json_text() -> None:
    parsed = parse_document_analysis_response(
        """Here is the requested analysis:
        {
          "announcement_overview": {
            "title": "Prepare launch",
            "main_purpose": "Prepare launch",
            "project_type": "",
            "support_summary": ""
          },
          "consortium_requirements": {},
          "eligibility_by_role": [],
          "recommended_consortium_strategy": {},
          "budget": {},
          "submission_documents": [],
          "presentation": {},
          "application_schedule": {},
          "submission_channel": {},
          "contacts": [],
          "risks_and_checks": {},
          "internal_execution_plan": {
            "team_assignments": [{"team_member": "Platform Team", "responsibility": "Owner", "reason": ""}],
            "immediate_next_actions": []
          }
        }
        Hope this helps."""
    )

    assert parsed["announcement_overview"]["main_purpose"] == "Prepare launch"
    assert parsed["internal_execution_plan"]["team_assignments"][0]["team_member"] == "Platform Team"


def test_format_document_analysis_summary_renders_readable_text() -> None:
    text = format_document_analysis_summary(
        {
            "announcement_overview": {
                "title": "Funding notice",
                "main_purpose": "Coordinate a release",
                "project_type": "Commercialization",
                "support_summary": "Validation and certification support",
            },
            "recommended_consortium_strategy": {
                "recommended_structure": ["Lead organization + demand company"],
            },
            "internal_execution_plan": {
                "immediate_next_actions": ["Lock the publish checklist"],
            },
        }
    )

    assert "Title: Funding notice" in text
    assert "Main purpose: Coordinate a release" in text
    assert "- Lead organization + demand company" in text
    assert "- Lock the publish checklist" in text
