from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.release import ReleaseCheckItem, ReleaseManifest


def test_release_manifest_counts_are_validated() -> None:
    check = ReleaseCheckItem(name="version", status="PASS", message="ok")

    manifest = ReleaseManifest(
        version="0.1.0-mvp",
        generated_at=datetime.now(),
        project_root=".",
        python_version="3.12",
        checks_passed=True,
        pass_count=1,
        warn_count=0,
        fail_count=0,
        checks=[check],
        key_files={"VERSION": True},
        key_commands={"show_version": "python -m ashare_alpha show-version"},
        safety_summary={"offline_mode": True},
        summary="发布检查通过。",
    )

    assert manifest.checks_passed is True
    assert manifest.pass_count == 1


def test_release_manifest_rejects_mismatched_counts() -> None:
    check = ReleaseCheckItem(name="version", status="PASS", message="ok")

    with pytest.raises(ValidationError):
        ReleaseManifest(
            version="0.1.0-mvp",
            generated_at=datetime.now(),
            project_root=".",
            python_version="3.12",
            checks_passed=True,
            pass_count=0,
            warn_count=0,
            fail_count=0,
            checks=[check],
            key_files={},
            key_commands={},
            safety_summary={},
            summary="bad",
        )
