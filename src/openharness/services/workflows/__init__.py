"""Workflow entrypoints for domain-specific document tasks."""

from openharness.services.workflows.announcement import run_announcement_analysis
from openharness.services.workflows.base import DocumentWorkflowRequest, DocumentWorkflowResult
from openharness.services.workflows.proposal_ops import (
    ProposalOpsRequest,
    build_proposal_ops_preview,
)

__all__ = [
    "DocumentWorkflowRequest",
    "DocumentWorkflowResult",
    "ProposalOpsRequest",
    "build_proposal_ops_preview",
    "run_announcement_analysis",
]
