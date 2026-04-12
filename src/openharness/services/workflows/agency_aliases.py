"""Agency alias mapping for announcement folder names."""

from __future__ import annotations


from openharness.services.workflows.proposal_config import load_agency_aliases


def resolve_agency_label(value: str) -> str:
    """Return the managed abbreviation for an agency name, or the original name."""
    cleaned = value.strip()
    if not cleaned:
        return ""
    aliases = load_agency_aliases()
    if cleaned in aliases:
        return aliases[cleaned]
    normalized = _normalize(cleaned)
    for agency, abbreviation in aliases.items():
        if normalized == _normalize(agency):
            return abbreviation
    for agency, abbreviation in aliases.items():
        normalized_agency = _normalize(agency)
        if normalized_agency and normalized_agency in normalized:
            return abbreviation
    return cleaned


def _normalize(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())
