from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ReleaseCheckStatus = Literal["PASS", "WARN", "FAIL"]


class ReleaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReleaseCheckItem(ReleaseModel):
    name: str = Field(min_length=1)
    status: ReleaseCheckStatus
    message: str = Field(min_length=1)
    recommendation: str | None = None


class ReleaseManifest(ReleaseModel):
    version: str = Field(min_length=1)
    generated_at: datetime
    project_root: str = Field(min_length=1)
    python_version: str = Field(min_length=1)
    checks_passed: bool
    pass_count: int = Field(ge=0)
    warn_count: int = Field(ge=0)
    fail_count: int = Field(ge=0)
    checks: list[ReleaseCheckItem] = Field(default_factory=list)
    key_files: dict[str, bool] = Field(default_factory=dict)
    key_commands: dict[str, str] = Field(default_factory=dict)
    safety_summary: dict[str, Any] = Field(default_factory=dict)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> ReleaseManifest:
        if self.pass_count != sum(1 for item in self.checks if item.status == "PASS"):
            raise ValueError("pass_count does not match checks")
        if self.warn_count != sum(1 for item in self.checks if item.status == "WARN"):
            raise ValueError("warn_count does not match checks")
        if self.fail_count != sum(1 for item in self.checks if item.status == "FAIL"):
            raise ValueError("fail_count does not match checks")
        if self.checks_passed != (self.fail_count == 0):
            raise ValueError("checks_passed must be true only when fail_count is 0")
        return self
