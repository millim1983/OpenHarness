"""Configuration loading for proposal automation workflows."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_DIR = REPO_ROOT / "proposal_assets" / "config"


def proposal_config_dir() -> Path:
    """Return the proposal automation config directory."""
    return Path(os.environ.get("OPENHARNESS_PROPOSAL_CONFIG_DIR", DEFAULT_CONFIG_DIR)).expanduser()


def load_proposal_config(name: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load one JSON config file from the proposal config directory."""
    path = proposal_config_dir() / name
    if not path.exists():
        return dict(default or {})
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Proposal config must be a JSON object: {path}")
    return payload


def load_feature_flags() -> dict[str, bool]:
    """Return proposal automation feature flags."""
    payload = load_proposal_config("feature_flags.json")
    return {key: bool(value) for key, value in payload.items()}


def feature_enabled(name: str, default: bool = False) -> bool:
    """Return whether a proposal automation feature is enabled."""
    return load_feature_flags().get(name, default)


def load_agency_aliases() -> dict[str, str]:
    """Return managed agency alias mappings."""
    payload = load_proposal_config("agency_aliases.json")
    return {str(key): str(value) for key, value in payload.items()}


def load_folder_rules() -> dict[str, Any]:
    """Return folder naming rules."""
    return load_proposal_config("folder_rules.json")


def load_folder_tree() -> list[str]:
    """Return the announcement project folder tree."""
    payload = load_proposal_config("folder_tree.json")
    folders = payload.get("announcement_project_folders", [])
    if not isinstance(folders, list):
        raise ValueError("`announcement_project_folders` must be a list.")
    return [str(folder) for folder in folders]
