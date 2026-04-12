"""Shared workflow data models for document-oriented business tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentWorkflowRequest:
    """Normalized input for one document workflow run."""

    profile_name: str
    file_name: str
    extracted_text: str
    system_prompt: str = ""
    instruction: str = ""
    team_context: str = ""


@dataclass(frozen=True)
class DocumentWorkflowResult:
    """Normalized result payload returned by a document workflow."""

    workflow_name: str
    summary: str
    structured: dict[str, Any]
    prompt_source_truncated: bool = False
