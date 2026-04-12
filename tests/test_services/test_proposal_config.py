from __future__ import annotations

import json
from pathlib import Path

from openharness.services.workflows.proposal_config import (
    feature_enabled,
    load_agency_aliases,
    load_folder_tree,
)


def test_proposal_config_loads_from_override_dir(tmp_path: Path, monkeypatch) -> None:
    config_dir = tmp_path / "proposal_config"
    config_dir.mkdir()
    (config_dir / "feature_flags.json").write_text(
        json.dumps({"announcement_agent": False}),
        encoding="utf-8",
    )
    (config_dir / "agency_aliases.json").write_text(
        json.dumps({"테스트기관": "TEST"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (config_dir / "folder_tree.json").write_text(
        json.dumps({"announcement_project_folders": ["00_source"]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENHARNESS_PROPOSAL_CONFIG_DIR", str(config_dir))

    assert feature_enabled("announcement_agent", True) is False
    assert load_agency_aliases()["테스트기관"] == "TEST"
    assert load_folder_tree() == ["00_source"]
