"""Agency alias mapping for announcement folder names."""

from __future__ import annotations


AGENCY_ALIASES: dict[str, str] = {
    "한국산업기술진흥원": "KIAT",
    "KIAT": "KIAT",
    "한국산업기술기획평가원": "KEIT",
    "KEIT": "KEIT",
    "중소기업기술정보진흥원": "TIPA",
    "TIPA": "TIPA",
    "정보통신기획평가원": "IITP",
    "IITP": "IITP",
    "한국에너지기술평가원": "KETEP",
    "KETEP": "KETEP",
    "한국콘텐츠진흥원": "KOCCA",
    "KOCCA": "KOCCA",
    "한국인터넷진흥원": "KISA",
    "KISA": "KISA",
    "한국지능정보사회진흥원": "NIA",
    "NIA": "NIA",
    "조달청": "PPS",
}


def resolve_agency_label(value: str) -> str:
    """Return the managed abbreviation for an agency name, or the original name."""
    cleaned = value.strip()
    if not cleaned:
        return ""
    if cleaned in AGENCY_ALIASES:
        return AGENCY_ALIASES[cleaned]
    normalized = _normalize(cleaned)
    for agency, abbreviation in AGENCY_ALIASES.items():
        if normalized == _normalize(agency):
            return abbreviation
    for agency, abbreviation in AGENCY_ALIASES.items():
        normalized_agency = _normalize(agency)
        if normalized_agency and normalized_agency in normalized:
            return abbreviation
    return cleaned


def _normalize(value: str) -> str:
    return "".join(char.lower() for char in value if char.isalnum())
