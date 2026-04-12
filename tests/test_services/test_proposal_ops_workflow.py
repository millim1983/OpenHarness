from __future__ import annotations

from openharness.services.workflows.proposal_ops import (
    ProposalOpsRequest,
    build_proposal_ops_preview,
)


def test_build_proposal_ops_preview_from_announcement_analysis() -> None:
    preview = build_proposal_ops_preview(
        ProposalOpsRequest(
            file_name="notice.pdf",
            structured_analysis={
                "announcement_overview": {
                    "title": "Smart Factory Support",
                    "project_type": "Non R&D support",
                    "support_summary": "Support implementation",
                },
                "application_schedule": {"submission_deadline": "2026-05-01 18:00"},
                "submission_channel": {"portal_or_address": "example.go.kr"},
                "submission_documents": [
                    {
                        "document_name": "Application form",
                        "required_for": ["lead"],
                    }
                ],
                "risks_and_checks": {
                    "missing_information": ["Confirm online portal account owner"]
                },
                "internal_execution_plan": {
                    "team_assignments": [
                        {"team_member": "Ops Lead", "responsibility": "Collect forms"}
                    ]
                },
            },
            team_context="Ops Lead: submission",
        )
    )

    assert preview["project_summary"]["title"] == "Smart Factory Support"
    assert preview["project_summary"]["submission_deadline"] == "2026-05-01 18:00"
    assert preview["submission_checklist"][0]["item"] == "제출 마감 재확인"
    assert preview["submission_checklist"][1]["item"] == "Application form"
    assert preview["manager_questions"][0]["question"] == "Confirm online portal account owner"
    assert preview["role_tasks"][0]["owner"] == "Ops Lead"
    assert preview["folder_plan"][0].startswith("proposal_ops/")
