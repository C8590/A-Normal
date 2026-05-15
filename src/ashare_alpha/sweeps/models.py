from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SweepCommand = Literal["run-pipeline", "run-backtest", "train-probability-model"]
SweepRunStatus = Literal["SUCCESS", "PARTIAL", "FAILED"]


class SweepModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class SweepVariant(SweepModel):
    name: str = Field(min_length=1)
    description: str | None = None
    config_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    command_args: dict[str, Any] | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
            raise ValueError("variant name may contain only letters, digits, underscores, and hyphens")
        return value


class SweepSpec(SweepModel):
    sweep_name: str = Field(min_length=1)
    description: str | None = None
    command: SweepCommand
    base_config_dir: str = Field(min_length=1)
    data_dir: str | None = None
    output_root_dir: str = Field(min_length=1)
    experiment_registry_dir: str = Field(min_length=1)
    common_args: dict[str, Any] = Field(default_factory=dict)
    variants: list[SweepVariant] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class SweepRunRecord(SweepModel):
    variant_name: str = Field(min_length=1)
    status: SweepRunStatus
    experiment_id: str | None = None
    config_dir: str = Field(min_length=1)
    output_dir: str = Field(min_length=1)
    metrics: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = None


class SweepResult(SweepModel):
    sweep_id: str = Field(min_length=1)
    sweep_name: str = Field(min_length=1)
    command: SweepCommand
    generated_at: datetime
    base_config_dir: str = Field(min_length=1)
    output_dir: str = Field(min_length=1)
    registry_dir: str = Field(min_length=1)
    total_variants: int = Field(ge=0)
    success_count: int = Field(ge=0)
    partial_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    runs: list[SweepRunRecord] = Field(default_factory=list)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> SweepResult:
        if self.total_variants != len(self.runs):
            raise ValueError("total_variants must equal len(runs)")
        if self.success_count != sum(1 for run in self.runs if run.status == "SUCCESS"):
            raise ValueError("success_count does not match runs")
        if self.partial_count != sum(1 for run in self.runs if run.status == "PARTIAL"):
            raise ValueError("partial_count does not match runs")
        if self.failed_count != sum(1 for run in self.runs if run.status == "FAILED"):
            raise ValueError("failed_count does not match runs")
        return self
