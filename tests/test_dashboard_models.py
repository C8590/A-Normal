from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.dashboard import DashboardArtifact, DashboardIndex, DashboardSummary


def test_dashboard_artifact_valid() -> None:
    artifact = DashboardArtifact(
        artifact_id="pipeline:1",
        artifact_type="pipeline",
        name="pipeline",
        path="outputs/pipelines/pipeline/manifest.json",
    )

    assert artifact.artifact_type == "pipeline"


def test_dashboard_artifact_invalid_type_raises() -> None:
    with pytest.raises(ValidationError):
        DashboardArtifact(artifact_id="bad", artifact_type="best", name="bad", path="bad.json")


def test_dashboard_index_serializes() -> None:
    artifact = DashboardArtifact(artifact_id="pipeline:1", artifact_type="pipeline", name="pipeline", path="manifest.json")
    index = DashboardIndex(
        generated_at=datetime(2026, 5, 14, 12, 0, 0),
        outputs_root="outputs",
        artifact_count=1,
        artifacts_by_type={"pipeline": 1},
        artifacts=[artifact],
    )

    assert index.model_dump(mode="json")["artifacts_by_type"]["pipeline"] == 1


def test_dashboard_summary_serializes() -> None:
    summary = DashboardSummary(
        generated_at=datetime(2026, 5, 14, 12, 0, 0),
        outputs_root="outputs",
        summary_text="仅用于研究汇总。",
    )

    assert summary.model_dump(mode="json")["summary_text"] == "仅用于研究汇总。"
