from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DataValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)


class DataValidationError(Exception):
    """Raised when local input data cannot be loaded or validated."""
