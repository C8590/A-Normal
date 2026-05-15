from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ExternalIssueSeverity = Literal["info", "warning", "error"]


class ExternalContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ExternalDatasetContract(ExternalContractModel):
    source_name: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    target_dataset_name: str = Field(min_length=1)
    description: str | None = None


class ExternalContractValidationIssue(ExternalContractModel):
    severity: ExternalIssueSeverity
    source_name: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    issue_type: str = Field(min_length=1)
    field_name: str | None = None
    message: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class ExternalContractValidationReport(ExternalContractModel):
    source_name: str = Field(min_length=1)
    fixture_dir: str
    generated_at: datetime
    total_issues: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    passed: bool
    issues: list[ExternalContractValidationIssue] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> ExternalContractValidationReport:
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
