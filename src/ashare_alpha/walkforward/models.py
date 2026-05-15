from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


WalkForwardCommand = Literal["run-backtest", "run-sweep"]
WalkForwardStatus = Literal["SUCCESS", "PARTIAL", "FAILED", "SKIPPED"]


class WalkForwardModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class WalkForwardSpec(WalkForwardModel):
    name: str = Field(min_length=1)
    description: str | None = None
    command: WalkForwardCommand
    data_dir: str = Field(min_length=1)
    base_config_dir: str = Field(min_length=1)
    output_root_dir: str = Field(min_length=1)
    experiment_registry_dir: str = Field(min_length=1)
    start_date: date
    end_date: date
    train_window_days: int | None = Field(default=None, gt=0)
    test_window_days: int = Field(gt=0)
    step_days: int = Field(gt=0)
    min_test_trading_days: int = Field(ge=1)
    common_args: dict[str, Any] = Field(default_factory=dict)
    sweep_spec: str | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_spec(self) -> WalkForwardSpec:
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be earlier than end_date")
        if self.command == "run-sweep" and not self.sweep_spec:
            raise ValueError("sweep_spec is required when command=run-sweep")
        return self


class WalkForwardFold(WalkForwardModel):
    fold_index: int = Field(ge=1)
    train_start: date | None = None
    train_end: date | None = None
    test_start: date
    test_end: date
    status: WalkForwardStatus = "SKIPPED"
    experiment_id: str | None = None
    output_dir: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> WalkForwardFold:
        if self.test_start > self.test_end:
            raise ValueError("test_start must be on or before test_end")
        if (self.train_start is None) != (self.train_end is None):
            raise ValueError("train_start and train_end must be provided together")
        if self.train_start is not None and self.train_end is not None and self.train_start > self.train_end:
            raise ValueError("train_start must be on or before train_end")
        return self


class WalkForwardResult(WalkForwardModel):
    walkforward_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    command: WalkForwardCommand
    generated_at: datetime
    start_date: date
    end_date: date
    fold_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    folds: list[WalkForwardFold] = Field(default_factory=list)
    stability_metrics: dict[str, Any] = Field(default_factory=dict)
    overfit_warnings: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> WalkForwardResult:
        if self.fold_count != len(self.folds):
            raise ValueError("fold_count must equal len(folds)")
        if self.success_count != sum(1 for fold in self.folds if fold.status in {"SUCCESS", "PARTIAL"}):
            raise ValueError("success_count does not match folds")
        if self.failed_count != sum(1 for fold in self.folds if fold.status == "FAILED"):
            raise ValueError("failed_count does not match folds")
        if self.skipped_count != sum(1 for fold in self.folds if fold.status == "SKIPPED"):
            raise ValueError("skipped_count does not match folds")
        return self
