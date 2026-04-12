"""Announcement-analysis workflow built on top of the generic document layer."""

from __future__ import annotations

from openharness.services.document_processing import (
    build_document_analysis_prompt,
    format_document_analysis_summary,
    parse_document_analysis_response,
)
from openharness.services.web_runtime import run_single_prompt_sync
from openharness.services.workflows.base import DocumentWorkflowRequest, DocumentWorkflowResult


def run_announcement_analysis(request: DocumentWorkflowRequest, *, cwd: str) -> DocumentWorkflowResult:
    """Analyze one announcement document and return structured workflow output."""

    analysis_prompt, truncated = build_document_analysis_prompt(
        request.file_name,
        request.extracted_text,
        instruction=request.instruction,
        team_context=request.team_context,
        system_prompt=request.system_prompt,
    )
    raw_result = run_single_prompt_sync(
        profile_name=request.profile_name,
        message=analysis_prompt,
        cwd=cwd,
        system_prompt=request.system_prompt,
    )
    analysis = parse_document_analysis_response(raw_result["answer"])
    summary_text = format_document_analysis_summary(analysis) or raw_result["answer"]
    return DocumentWorkflowResult(
        workflow_name="announcement_analysis",
        summary=summary_text,
        structured=analysis,
        prompt_source_truncated=truncated,
    )
