from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


QualitySeverity = Literal["info", "warning", "error"]


class QualityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class QualityIssue(QualityModel):
    severity: QualitySeverity
    dataset_name: str = Field(min_length=1)
    issue_type: str = Field(min_length=1)
    ts_code: str | None = None
    trade_date: date | None = None
    field_name: str | None = None
    message: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class DataQualityReport(QualityModel):
    generated_at: datetime
    data_dir: str
    source_name: str | None = None
    data_version: str | None = None
    total_issues: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    row_counts: dict[str, int] = Field(default_factory=dict)
    coverage: dict[str, Any] = Field(default_factory=dict)
    issues: list[QualityIssue] = Field(default_factory=list)
    passed: bool
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> DataQualityReport:
        if self.total_issues != len(self.issues):
            raise ValueError("total_issues must equal len(issues)")
        if self.error_count != sum(1 for issue in self.issues if issue.severity == "error"):
            raise ValueError("error_count does not match issues")
        if self.warning_count != sum(1 for issue in self.issues if issue.severity == "warning"):
            raise ValueError("warning_count does not match issues")
        if self.info_count != sum(1 for issue in self.issues if issue.severity == "info"):
            raise ValueError("info_count does not match issues")
        if self.passed != (self.error_count == 0):
            raise ValueError("passed must be true only when error_count is 0")
        return self
