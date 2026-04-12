from __future__ import annotations

from openharness.services.workflows import DocumentWorkflowRequest, run_announcement_analysis


def test_run_announcement_analysis_returns_structured_result(monkeypatch) -> None:
    monkeypatch.setattr(
        "openharness.services.workflows.announcement.run_single_prompt_sync",
        lambda **kwargs: {
            "profile": kwargs["profile_name"],
            "answer": """
            {
              "announcement_overview": {
                "title": "Funding notice",
                "main_purpose": "Support commercialization",
                "project_type": "Commercialization",
                "support_summary": "Validation support"
              },
              "consortium_requirements": {},
              "eligibility_by_role": [],
              "recommended_consortium_strategy": {
                "recommended_structure": ["Lead org plus demand company"]
              },
              "budget": {},
              "submission_documents": [],
              "presentation": {},
              "application_schedule": {},
              "submission_channel": {},
              "contacts": [],
              "risks_and_checks": {},
              "internal_execution_plan": {
                "immediate_next_actions": ["Draft the consortium note"]
              }
            }
            """,
        },
    )

    result = run_announcement_analysis(
        DocumentWorkflowRequest(
            profile_name="gemini-compatible",
            file_name="notice.pdf",
            extracted_text="Announcement body",
            instruction="Focus on structure",
            team_context="Alex PM: submission lead",
        ),
        cwd="/tmp/project",
    )

    assert result.workflow_name == "announcement_analysis"
    assert result.structured["announcement_overview"]["title"] == "Funding notice"
    assert "Lead org plus demand company" in result.summary
