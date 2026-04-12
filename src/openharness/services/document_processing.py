"""Helpers for extracting text from uploaded documents for the web MVP."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree


MAX_SUMMARY_SOURCE_CHARS = 12000
WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
TEXT_EXTENSIONS = {
    ".csv",
    ".html",
    ".json",
    ".log",
    ".md",
    ".py",
    ".rst",
    ".text",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}


def extract_text_from_document(filename: str, data: bytes) -> str:
    """Extract plain text from a small uploaded document."""
    suffix = Path(filename).suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        return _decode_text_bytes(data)
    if suffix == ".docx":
        return _extract_docx_text(data)
    if suffix == ".pdf":
        return _extract_pdf_text(data)

    try:
        return _decode_text_bytes(data)
    except UnicodeDecodeError as exc:
        raise ValueError(f"Unsupported file type for text extraction: {suffix or 'unknown'}") from exc


def build_document_summary_prompt(
    filename: str,
    extracted_text: str,
    instruction: str = "",
) -> tuple[str, bool]:
    """Build a one-shot summary prompt from extracted document text."""
    cleaned = extracted_text.strip()
    if not cleaned:
        raise ValueError("The uploaded file did not contain extractable text.")

    truncated = len(cleaned) > MAX_SUMMARY_SOURCE_CHARS
    source_text = cleaned[:MAX_SUMMARY_SOURCE_CHARS]
    if truncated:
        source_text += "\n\n[Truncated for MVP summarization]"

    prompt_parts = [
        "You are summarizing one uploaded document for a lightweight web MVP.",
        f"Filename: {filename}",
        "Task:",
        "- Identify the document's main purpose.",
        "- Summarize the most important points in 3-6 bullets.",
        "- End with a short 'Recommended next action' line.",
    ]
    if instruction.strip():
        prompt_parts.extend(
            [
                "Additional user instruction:",
                instruction.strip(),
            ]
        )
    prompt_parts.extend(
        [
            "Document text:",
            source_text,
        ]
    )
    return "\n".join(prompt_parts), truncated


def build_document_analysis_prompt(
    filename: str,
    extracted_text: str,
    instruction: str = "",
    team_context: str = "",
    system_prompt: str = "",
) -> tuple[str, bool]:
    """Build a one-shot structured analysis prompt from extracted document text."""
    cleaned = extracted_text.strip()
    if not cleaned:
        raise ValueError("The uploaded file did not contain extractable text.")

    truncated = len(cleaned) > MAX_SUMMARY_SOURCE_CHARS
    source_text = cleaned[:MAX_SUMMARY_SOURCE_CHARS]
    if truncated:
        source_text += "\n\n[Truncated for MVP analysis]"

    prompt_parts = [
        "You are analyzing one uploaded government announcement for a lightweight web MVP.",
        f"Filename: {filename}",
        "Return only valid JSON with this exact schema:",
        '{'
        '"announcement_overview": {"title": "string", "main_purpose": "string", "project_type": "string", "support_summary": "string"}, '
        '"consortium_requirements": {"consortium_required": "boolean", "demand_company_required": "boolean", "lead_org_allowed": ["string"], "partner_org_allowed": ["string"], "subcontractor_allowed": "boolean", "notes": ["string"]}, '
        '"eligibility_by_role": [{"role": "string", "eligible_entities": ["string"], "restrictions": ["string"]}], '
        '"recommended_consortium_strategy": {"recommended_structure": ["string"], "recommended_role_rr": [{"role": "string", "recommended_entity_type": "string", "responsibilities": ["string"]}], "key_differentiators": ["string"]}, '
        '"budget": {"total_amount": "string", "by_year": [{"year": "string", "amount": "string"}], "matching_requirement": "string", "additional_info_needed": ["string"]}, '
        '"submission_documents": [{"document_name": "string", "required_for": ["string"], "provided_form": "boolean", "issuance_source": "string", "notes": "string"}], '
        '"presentation": {"required": "boolean", "notes": "string"}, '
        '"application_schedule": {"announcement_date": "string", "start_at": "string", "end_at": "string", "submission_deadline": "string", "important_milestones": [{"date": "string", "label": "string"}]}, '
        '"submission_channel": {"method": "string", "portal_or_address": "string", "notes": "string"}, '
        '"contacts": [{"organization": "string", "name": "string", "phone": "string", "email": "string", "topic": "string"}], '
        '"risks_and_checks": {"compliance_risks": ["string"], "missing_information": ["string"], "go_no_go_checks": ["string"]}, '
        '"internal_execution_plan": {"team_assignments": [{"team_member": "string", "responsibility": "string", "reason": "string"}], "immediate_next_actions": ["string"]}'
        '}',
        "Rules:",
        '- Use empty strings, empty arrays, or false when the document does not provide a value.',
        '- Extract announcement facts from the document first, then provide strategy recommendations separately.',
        '- Do not invent eligibility or consortium rules that are not supported by the announcement.',
        '- Preserve uncertain dates as written instead of inventing exact dates.',
        '- If budget breakdown, forms, or presentation details are missing, record that in additional_info_needed or missing_information.',
        '- For internal_execution_plan.team_assignments, use the provided team context when available. If team context is missing, leave team_assignments empty.',
    ]
    if system_prompt.strip():
        prompt_parts.extend(
            [
                "Project system prompt:",
                system_prompt.strip(),
            ]
        )
    if instruction.strip():
        prompt_parts.extend(
            [
                "Additional user instruction:",
                instruction.strip(),
            ]
        )
    if team_context.strip():
        prompt_parts.extend(
            [
                "Team context for internal execution planning:",
                team_context.strip(),
            ]
        )
    prompt_parts.extend(
        [
            "Document text:",
            source_text,
        ]
    )
    return "\n".join(prompt_parts), truncated


def parse_document_analysis_response(response_text: str) -> dict[str, object]:
    """Parse and normalize the model's JSON analysis response."""
    candidate_text = _extract_json_candidate(response_text)
    try:
        parsed = json.loads(candidate_text)
    except json.JSONDecodeError as exc:
        raise ValueError("The model did not return valid JSON for document analysis.") from exc

    if not isinstance(parsed, dict):
        parsed = {}

    return {
        "announcement_overview": _normalize_overview(parsed.get("announcement_overview")),
        "consortium_requirements": _normalize_consortium_requirements(parsed.get("consortium_requirements")),
        "eligibility_by_role": _normalize_eligibility_by_role(parsed.get("eligibility_by_role")),
        "recommended_consortium_strategy": _normalize_strategy(parsed.get("recommended_consortium_strategy")),
        "budget": _normalize_budget(parsed.get("budget")),
        "submission_documents": _normalize_submission_documents(parsed.get("submission_documents")),
        "presentation": _normalize_presentation(parsed.get("presentation")),
        "application_schedule": _normalize_application_schedule(parsed.get("application_schedule")),
        "submission_channel": _normalize_submission_channel(parsed.get("submission_channel")),
        "contacts": _normalize_contacts(parsed.get("contacts")),
        "risks_and_checks": _normalize_risks_and_checks(parsed.get("risks_and_checks")),
        "internal_execution_plan": _normalize_internal_execution_plan(parsed.get("internal_execution_plan")),
    }


def format_document_analysis_summary(analysis: dict[str, object]) -> str:
    """Render a readable text summary from structured analysis."""
    overview = analysis.get("announcement_overview", {})
    strategy = analysis.get("recommended_consortium_strategy", {})
    internal_plan = analysis.get("internal_execution_plan", {})
    if not isinstance(overview, dict):
        overview = {}
    if not isinstance(strategy, dict):
        strategy = {}
    if not isinstance(internal_plan, dict):
        internal_plan = {}
    lines = []
    title = _string_value(overview, "title")
    if title:
        lines.append(f"Title: {title}")
    main_purpose = _string_value(overview, "main_purpose")
    if main_purpose:
        lines.append(f"Main purpose: {main_purpose}")
    support_summary = _string_value(overview, "support_summary")
    if support_summary:
        lines.append(f"Support summary: {support_summary}")
    recommended_structure = _string_list(strategy.get("recommended_structure", []))
    if recommended_structure:
        lines.append("Recommended consortium structure:")
        lines.extend(f"- {item}" for item in recommended_structure)
    next_actions = _string_list(internal_plan.get("immediate_next_actions", []))
    if next_actions:
        lines.append("Immediate next actions:")
        lines.extend(f"- {item}" for item in next_actions[:4])
    return "\n".join(lines).strip()


def _decode_text_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp949"):
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if _looks_like_text(text):
            return text
    try:
        text = data.decode("latin-1")
    except UnicodeDecodeError as exc:
        raise UnicodeDecodeError("text", b"", 0, 1, "Unable to decode text bytes") from exc
    if _looks_like_text(text):
        return text
    raise UnicodeDecodeError("text", b"", 0, 1, "Unable to decode text bytes")


def _looks_like_text(text: str) -> bool:
    if not text:
        return True

    suspicious = 0
    for char in text:
        codepoint = ord(char)
        if codepoint == 9 or codepoint == 10 or codepoint == 13:
            continue
        if 32 <= codepoint <= 126:
            continue
        if char.isprintable():
            continue
        suspicious += 1

    return suspicious / max(len(text), 1) < 0.05


def _string_value(payload: dict[str, object] | object, key: str) -> str:
    if not isinstance(payload, dict):
        return ""
    value = payload.get(key, "")
    return value.strip() if isinstance(value, str) else ""


def _string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def _bool_value(payload: dict[str, object] | object, key: str) -> bool:
    if not isinstance(payload, dict):
        return False
    value = payload.get(key, False)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"true", "yes", "required", "allowed", "y"}
    return False


def _normalize_overview(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    return {
        "title": _string_value(payload, "title"),
        "main_purpose": _string_value(payload, "main_purpose"),
        "project_type": _string_value(payload, "project_type"),
        "support_summary": _string_value(payload, "support_summary"),
    }


def _normalize_consortium_requirements(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    return {
        "consortium_required": _bool_value(payload, "consortium_required"),
        "demand_company_required": _bool_value(payload, "demand_company_required"),
        "lead_org_allowed": _string_list(payload.get("lead_org_allowed")),
        "partner_org_allowed": _string_list(payload.get("partner_org_allowed")),
        "subcontractor_allowed": _bool_value(payload, "subcontractor_allowed"),
        "notes": _string_list(payload.get("notes")),
    }


def _normalize_eligibility_by_role(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "role": _string_value(item, "role"),
                "eligible_entities": _string_list(item.get("eligible_entities")),
                "restrictions": _string_list(item.get("restrictions")),
            }
        )
    return items


def _normalize_strategy(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    role_rr_raw = payload.get("recommended_role_rr")
    role_rr: list[dict[str, object]] = []
    if isinstance(role_rr_raw, list):
        for item in role_rr_raw:
            if not isinstance(item, dict):
                continue
            role_rr.append(
                {
                    "role": _string_value(item, "role"),
                    "recommended_entity_type": _string_value(item, "recommended_entity_type"),
                    "responsibilities": _string_list(item.get("responsibilities")),
                }
            )
    return {
        "recommended_structure": _string_list(payload.get("recommended_structure")),
        "recommended_role_rr": role_rr,
        "key_differentiators": _string_list(payload.get("key_differentiators")),
    }


def _normalize_budget(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    by_year_raw = payload.get("by_year")
    by_year: list[dict[str, str]] = []
    if isinstance(by_year_raw, list):
        for item in by_year_raw:
            if not isinstance(item, dict):
                continue
            by_year.append(
                {
                    "year": _string_value(item, "year"),
                    "amount": _string_value(item, "amount"),
                }
            )
    return {
        "total_amount": _string_value(payload, "total_amount"),
        "by_year": by_year,
        "matching_requirement": _string_value(payload, "matching_requirement"),
        "additional_info_needed": _string_list(payload.get("additional_info_needed")),
    }


def _normalize_submission_documents(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "document_name": _string_value(item, "document_name"),
                "required_for": _string_list(item.get("required_for")),
                "provided_form": _bool_value(item, "provided_form"),
                "issuance_source": _string_value(item, "issuance_source"),
                "notes": _string_value(item, "notes"),
            }
        )
    return items


def _normalize_presentation(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    return {
        "required": _bool_value(payload, "required"),
        "notes": _string_value(payload, "notes"),
    }


def _normalize_application_schedule(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    milestones_raw = payload.get("important_milestones")
    milestones: list[dict[str, str]] = []
    if isinstance(milestones_raw, list):
        for item in milestones_raw:
            if not isinstance(item, dict):
                continue
            milestones.append(
                {
                    "date": _string_value(item, "date"),
                    "label": _string_value(item, "label"),
                }
            )
    return {
        "announcement_date": _string_value(payload, "announcement_date"),
        "start_at": _string_value(payload, "start_at"),
        "end_at": _string_value(payload, "end_at"),
        "submission_deadline": _string_value(payload, "submission_deadline"),
        "important_milestones": milestones,
    }


def _normalize_submission_channel(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    return {
        "method": _string_value(payload, "method"),
        "portal_or_address": _string_value(payload, "portal_or_address"),
        "notes": _string_value(payload, "notes"),
    }


def _normalize_contacts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        items.append(
            {
                "organization": _string_value(item, "organization"),
                "name": _string_value(item, "name"),
                "phone": _string_value(item, "phone"),
                "email": _string_value(item, "email"),
                "topic": _string_value(item, "topic"),
            }
        )
    return items


def _normalize_risks_and_checks(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    return {
        "compliance_risks": _string_list(payload.get("compliance_risks")),
        "missing_information": _string_list(payload.get("missing_information")),
        "go_no_go_checks": _string_list(payload.get("go_no_go_checks")),
    }


def _normalize_internal_execution_plan(value: object) -> dict[str, object]:
    payload = value if isinstance(value, dict) else {}
    assignments_raw = payload.get("team_assignments")
    assignments: list[dict[str, object]] = []
    if isinstance(assignments_raw, list):
        for item in assignments_raw:
            if not isinstance(item, dict):
                continue
            assignments.append(
                {
                    "team_member": _string_value(item, "team_member"),
                    "responsibility": _string_value(item, "responsibility"),
                    "reason": _string_value(item, "reason"),
                }
            )
    return {
        "team_assignments": assignments,
        "immediate_next_actions": _string_list(payload.get("immediate_next_actions")),
    }


def _extract_json_candidate(response_text: str) -> str:
    text = response_text.strip()
    if not text:
        return text

    fenced = _extract_fenced_block(text)
    if fenced is not None:
        return fenced

    object_text = _extract_balanced_json_object(text)
    if object_text is not None:
        return object_text

    return text


def _extract_fenced_block(text: str) -> str | None:
    fence = "```"
    if fence not in text:
        return None

    parts = text.split(fence)
    for block in parts[1:]:
        lines = block.splitlines()
        if not lines:
            continue
        first = lines[0].strip().lower()
        body_lines = lines[1:] if first in {"json", ""} else lines
        candidate = "\n".join(body_lines).strip()
        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate
    return None


def _extract_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
            continue
        if char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1].strip()

    return None


def _extract_docx_text(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml_bytes = archive.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("The .docx file is missing document.xml.") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError("The uploaded .docx file is invalid.") from exc

    root = ElementTree.fromstring(xml_bytes)
    paragraphs = []
    for paragraph in root.findall(".//w:p", WORD_NAMESPACE):
        runs = [node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE)]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs).strip()


def _extract_pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError(
            "PDF extraction requires the `pypdf` package. In WSL, activate the project venv and run `uv sync`."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:  # pragma: no cover - parser-specific failures
        raise ValueError("The uploaded PDF could not be read.") from exc

    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append(text)
    return "\n\n".join(pages).strip()
