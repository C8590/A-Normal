from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AdjustedResearchStepStatus = Literal["SUCCESS", "SKIPPED", "FAILED"]
AdjustedResearchReportStatus = Literal["SUCCESS", "PARTIAL", "FAILED"]


class AdjustedResearchModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class AdjustedResearchStepResult(AdjustedResearchModel):
    name: str = Field(min_length=1)
    status: AdjustedResearchStepStatus
    started_at: datetime
    finished_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    output_paths: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_finished_step(self) -> AdjustedResearchStepResult:
        if self.status == "FAILED" and not self.error_message:
            raise ValueError("failed steps must include error_message")
        return self


class AdjustedFactorComparisonSummary(AdjustedResearchModel):
    left_price_source: str = Field(min_length=1)
    right_price_source: str = Field(min_length=1)
    compared_count: int = Field(ge=0)
    changed_ma20_count: int = Field(ge=0)
    changed_ma60_count: int = Field(ge=0)
    max_abs_momentum_20d_diff: float | None = None
    max_abs_momentum_60d_diff: float | None = None
    max_abs_volatility_20d_diff: float | None = None
    top_differences: list[dict[str, Any]] = Field(default_factory=list)


class AdjustedBacktestComparisonSummary(AdjustedResearchModel):
    left_price_source: str = Field(min_length=1)
    right_price_source: str = Field(min_length=1)
    total_return_diff: float | None = None
    annualized_return_diff: float | None = None
    max_drawdown_diff: float | None = None
    sharpe_diff: float | None = None
    final_equity_diff: float | None = None
    trade_count_diff: int | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class AdjustedResearchReport(AdjustedResearchModel):
    report_id: str = Field(min_length=1)
    generated_at: datetime
    data_dir: str = Field(min_length=1)
    config_dir: str = Field(min_length=1)
    target_date: date
    start_date: date
    end_date: date
    status: AdjustedResearchReportStatus
    steps: list[AdjustedResearchStepResult] = Field(default_factory=list)
    factor_comparisons: list[AdjustedFactorComparisonSummary] = Field(default_factory=list)
    backtest_comparisons: list[AdjustedBacktestComparisonSummary] = Field(default_factory=list)
    warning_items: list[str] = Field(default_factory=list)
    output_dir: str = Field(min_length=1)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_date_range(self) -> AdjustedResearchReport:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be earlier than end_date")
        return self
