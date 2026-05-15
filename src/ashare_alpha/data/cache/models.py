from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


CacheStatus = Literal["RAW_CACHED", "NORMALIZED", "FAILED"]


class CacheModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class CacheFile(CacheModel):
    dataset_name: str = Field(min_length=1)
    relative_path: str = Field(min_length=1)
    rows: int = Field(ge=0)
    sha256: str = Field(min_length=1)


class CacheManifest(CacheModel):
    cache_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    cache_version: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    cache_dir: str = Field(min_length=1)
    raw_dir: str = Field(min_length=1)
    normalized_dir: str = Field(min_length=1)
    mapping_path: str | None = None
    raw_files: list[CacheFile] = Field(default_factory=list)
    normalized_files: list[CacheFile] = Field(default_factory=list)
    raw_contract_passed: bool
    normalized_validation_passed: bool | None = None
    normalized_row_counts: dict[str, int] = Field(default_factory=dict)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    status: CacheStatus
    error_message: str | None = None
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_status(self) -> CacheManifest:
        if self.status == "FAILED" and not self.error_message:
            raise ValueError("FAILED cache manifest must include error_message")
        if self.status in {"RAW_CACHED", "NORMALIZED"} and self.error_message:
            raise ValueError("successful cache manifest must not include error_message")
        if self.status == "NORMALIZED" and self.normalized_validation_passed is not True:
            raise ValueError("NORMALIZED cache manifest must have normalized_validation_passed=true")
        return self


class CacheValidationReport(CacheModel):
    source_name: str = Field(min_length=1)
    cache_version: str = Field(min_length=1)
    generated_at: datetime
    cache_dir: str = Field(min_length=1)
    raw_contract_passed: bool
    normalized_validation_passed: bool | None = None
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    raw_row_counts: dict[str, int] = Field(default_factory=dict)
    normalized_row_counts: dict[str, int] = Field(default_factory=dict)
    summary: str = Field(min_length=1)


class CacheOperationResult(CacheModel):
    source_name: str = Field(min_length=1)
    cache_version: str = Field(min_length=1)
    cache_dir: str = Field(min_length=1)
    status: CacheStatus
    manifest_path: str = Field(min_length=1)
    raw_dir: str = Field(min_length=1)
    normalized_dir: str = Field(min_length=1)
    raw_file_count: int = Field(ge=0)
    normalized_file_count: int = Field(ge=0)
    validation_passed: bool | None = None
    error_message: str | None = None
    summary: str = Field(min_length=1)
