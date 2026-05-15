from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


PIPELINE_DISCLAIMER = (
    "本流水线仅用于研究和回测，不构成投资建议，不承诺收益，不会自动下单，也未接入券商接口。"
)

StepStatus = Literal["SUCCESS", "SKIPPED", "FAILED"]
PipelineStatus = Literal["SUCCESS", "PARTIAL", "FAILED"]


class PipelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PipelineStepResult(PipelineModel):
    name: str = Field(min_length=1)
    status: StepStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    output_paths: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> PipelineStepResult:
        if self.status == "FAILED" and not self.error_message:
            raise ValueError("error_message must not be empty when status is FAILED")
        if self.status == "SUCCESS" and self.finished_at is None:
            raise ValueError("finished_at must not be empty when status is SUCCESS")
        return self


class PipelineManifest(PipelineModel):
    pipeline_date: date
    generated_at: datetime
    data_dir: str
    config_dir: str
    output_dir: str
    model_dir: str | None = None

    status: PipelineStatus
    steps: list[PipelineStepResult] = Field(default_factory=list)

    total_stocks: int | None = None
    allowed_universe_count: int | None = None
    buy_count: int | None = None
    watch_count: int | None = None
    block_count: int | None = None
    high_risk_count: int | None = None
    market_regime: str | None = None
    probability_predictable_count: int | None = None

    daily_report_path: str | None = None
    universe_csv_path: str | None = None
    factor_csv_path: str | None = None
    event_csv_path: str | None = None
    signal_csv_path: str | None = None
    probability_csv_path: str | None = None
    leakage_audit_path: str | None = None
    quality_report_path: str | None = None

    disclaimer: str = PIPELINE_DISCLAIMER
