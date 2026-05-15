from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ashare_alpha.release import ReleaseCheckItem, ReleaseManifest, save_release_checklist_md, save_release_manifest_json


def test_release_manifest_json_can_be_saved(tmp_path: Path) -> None:
    manifest = _manifest()
    path = tmp_path / "release_manifest.json"

    save_release_manifest_json(manifest, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["version"] == "0.1.0-mvp"
    assert payload["checks_passed"] is True


def test_release_checklist_md_can_be_saved(tmp_path: Path) -> None:
    manifest = _manifest()
    path = tmp_path / "release_checklist.md"

    save_release_checklist_md(manifest, path)

    text = path.read_text(encoding="utf-8")
    assert "# Release Checklist" in text
    assert "0.1.0-mvp" in text


def _manifest() -> ReleaseManifest:
    return ReleaseManifest(
        version="0.1.0-mvp",
        generated_at=datetime.now(),
        project_root=".",
        python_version="3.12",
        checks_passed=True,
        pass_count=1,
        warn_count=0,
        fail_count=0,
        checks=[ReleaseCheckItem(name="version", status="PASS", message="ok")],
        key_files={"VERSION": True},
        key_commands={"show_version": "python -m ashare_alpha show-version"},
        safety_summary={"offline_mode": True},
        summary="发布检查通过。",
    )
