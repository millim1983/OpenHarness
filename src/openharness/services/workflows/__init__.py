"""Workflow entrypoints for domain-specific document tasks."""

from openharness.services.workflows.announcement import run_announcement_analysis
from openharness.services.workflows.base import DocumentWorkflowRequest, DocumentWorkflowResult

__all__ = [
    "DocumentWorkflowRequest",
    "DocumentWorkflowResult",
    "run_announcement_analysis",
]
