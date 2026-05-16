from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DashboardArtifactType = Literal[
    "pipeline",
    "backtest",
    "sweep",
    "walkforward",
    "experiment",
    "candidate_selection",
    "quality_report",
    "leakage_audit",
    "security_scan",
    "probability_model",
    "adjusted_research",
    "unknown",
]


class DashboardModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class DashboardArtifact(DashboardModel):
    artifact_id: str = Field(min_length=1)
    artifact_type: DashboardArtifactType
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    created_at: datetime | None = None
    status: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    related_paths: list[str] = Field(default_factory=list)


class DashboardIndex(DashboardModel):
    generated_at: datetime
    outputs_root: str = Field(min_length=1)
    artifact_count: int = Field(ge=0)
    artifacts_by_type: dict[str, int] = Field(default_factory=dict)
    artifacts: list[DashboardArtifact] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> DashboardIndex:
        if self.artifact_count != len(self.artifacts):
            raise ValueError("artifact_count must equal len(artifacts)")
        expected: dict[str, int] = {}
        for artifact in self.artifacts:
            expected[artifact.artifact_type] = expected.get(artifact.artifact_type, 0) + 1
        if self.artifacts_by_type != expected:
            raise ValueError("artifacts_by_type does not match artifacts")
        return self


class DashboardSummary(DashboardModel):
    generated_at: datetime
    outputs_root: str = Field(min_length=1)
    latest_pipeline: DashboardArtifact | None = None
    latest_backtest: DashboardArtifact | None = None
    latest_sweep: DashboardArtifact | None = None
    latest_walkforward: DashboardArtifact | None = None
    latest_adjusted_research: DashboardArtifact | None = None
    latest_candidate_selection: DashboardArtifact | None = None
    top_candidates: list[dict[str, Any]] = Field(default_factory=list)
    recent_experiments: list[dict[str, Any]] = Field(default_factory=list)
    warning_items: list[dict[str, Any]] = Field(default_factory=list)
    summary_text: str = Field(min_length=1)
