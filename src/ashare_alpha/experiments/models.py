from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ArtifactType = Literal["csv", "json", "markdown", "directory", "other"]
ExperimentStatus = Literal["SUCCESS", "FAILED", "PARTIAL"]
MetricValue = float | int | str | bool | None


class ExperimentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ExperimentArtifact(ExperimentModel):
    name: str = Field(min_length=1)
    path: str = Field(min_length=1)
    artifact_type: ArtifactType


class ExperimentMetric(ExperimentModel):
    name: str = Field(min_length=1)
    value: MetricValue
    category: str | None = None


class ExperimentRecord(ExperimentModel):
    experiment_id: str = Field(min_length=1)
    created_at: datetime
    command: str = Field(min_length=1)
    command_args: dict[str, Any] = Field(default_factory=dict)
    data_dir: str | None = None
    config_dir: str | None = None
    output_dir: str | None = None

    data_source: str | None = None
    data_version: str | None = None
    config_hash: str | None = None
    code_version: str | None = None

    status: ExperimentStatus
    metrics: list[ExperimentMetric] = Field(default_factory=list)
    artifacts: list[ExperimentArtifact] = Field(default_factory=list)
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_experiment_id(self) -> ExperimentRecord:
        if not self.experiment_id.startswith("exp_"):
            raise ValueError("experiment_id must start with exp_")
        return self


class ExperimentIndex(ExperimentModel):
    registry_dir: str
    generated_at: datetime
    experiments: list[ExperimentRecord] = Field(default_factory=list)


class ExperimentCompareResult(ExperimentModel):
    generated_at: datetime
    baseline_experiment_id: str
    target_experiment_id: str
    metric_diffs: dict[str, object] = Field(default_factory=dict)
    baseline: ExperimentRecord
    target: ExperimentRecord
    summary: str = Field(min_length=1)
