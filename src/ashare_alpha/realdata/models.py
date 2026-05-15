from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RealDataOfflineDrillStepStatus = Literal["SUCCESS", "SKIPPED", "FAILED"]
RealDataOfflineDrillStatus = Literal["SUCCESS", "PARTIAL", "FAILED"]


class RealDataOfflineDrillModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class RealDataOfflineDrillSpec(RealDataOfflineDrillModel):
    drill_name: str = Field(min_length=1)
    source_profile: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    data_version: str = Field(min_length=1)
    target_date: date
    output_root_dir: str = Field(min_length=1)
    experiment_registry_dir: str = Field(min_length=1)
    run_quality_report: bool = True
    run_leakage_audit: bool = True
    run_security_check: bool = True
    run_pipeline: bool = True
    build_frontend: bool = True
    build_dashboard: bool = True
    record_experiment: bool = True
    notes: str | None = None

    @field_validator("source_name")
    @classmethod
    def validate_source_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized.replace("_", "").isalnum():
            raise ValueError("source_name must contain lowercase letters, digits, and underscores only")
        return normalized

    @field_validator("data_version")
    @classmethod
    def validate_data_version(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.replace("_", "").replace("-", "").isalnum():
            raise ValueError("data_version must contain letters, digits, underscores, or hyphens only")
        return normalized


class RealDataOfflineDrillStep(RealDataOfflineDrillModel):
    name: str = Field(min_length=1)
    status: RealDataOfflineDrillStepStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    output_paths: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> RealDataOfflineDrillStep:
        if self.status == "FAILED" and not self.error_message:
            raise ValueError("FAILED step must include error_message")
        if self.status in {"SUCCESS", "SKIPPED"} and self.finished_at is None:
            raise ValueError("finished_at must be set for completed drill steps")
        return self


class RealDataOfflineDrillResult(RealDataOfflineDrillModel):
    drill_id: str = Field(min_length=1)
    drill_name: str = Field(min_length=1)
    generated_at: datetime
    source_name: str = Field(min_length=1)
    data_version: str = Field(min_length=1)
    target_date: date
    status: RealDataOfflineDrillStatus
    steps: list[RealDataOfflineDrillStep] = Field(default_factory=list)
    output_dir: str = Field(min_length=1)
    cache_dir: str | None = None
    materialized_data_dir: str | None = None
    imported_data_dir: str | None = None
    validation_report_path: str | None = None
    quality_report_dir: str | None = None
    leakage_audit_dir: str | None = None
    security_report_dir: str | None = None
    pipeline_output_dir: str | None = None
    frontend_output_dir: str | None = None
    dashboard_output_dir: str | None = None
    experiment_id: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)

    @property
    def failed_steps(self) -> list[RealDataOfflineDrillStep]:
        return [step for step in self.steps if step.status == "FAILED"]
