from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


IssueSeverity = Literal["info", "warning", "error"]


class AuditModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DataAvailabilityRecord(AuditModel):
    dataset_name: str = Field(min_length=1)
    ts_code: str | None = None
    data_date: date | None = None
    publish_time: datetime | None = None
    available_at: datetime
    source_name: str = Field(min_length=1)
    data_version: str = Field(min_length=1)
    row_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataSnapshot(AuditModel):
    snapshot_id: str = Field(min_length=1)
    created_at: datetime
    source_name: str
    data_version: str
    data_dir: str
    config_dir: str
    row_counts: dict[str, int] = Field(default_factory=dict)
    min_dates: dict[str, str | None] = Field(default_factory=dict)
    max_dates: dict[str, str | None] = Field(default_factory=dict)
    notes: str | None = None


class LeakageIssue(AuditModel):
    severity: IssueSeverity
    issue_type: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    ts_code: str | None = None
    trade_date: date | None = None
    data_date: date | None = None
    available_at: datetime | None = None
    message: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class LeakageAuditReport(AuditModel):
    audit_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    generated_at: datetime
    data_dir: str
    config_dir: str
    source_name: str
    data_version: str
    total_issues: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    issues: list[LeakageIssue] = Field(default_factory=list)
    passed: bool
    summary: str

    @model_validator(mode="after")
    def validate_counts(self) -> LeakageAuditReport:
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
