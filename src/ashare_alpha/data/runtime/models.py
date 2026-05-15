from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SourceRuntimeMode = Literal["offline_replay", "cache_only", "live_disabled"]
MaterializationStatus = Literal["SUCCESS", "FAILED"]


class RuntimeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class SourceProfile(RuntimeModel):
    source_name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    mode: SourceRuntimeMode
    contract_source_name: str = Field(min_length=1)
    mapping_path: str = Field(min_length=1)
    fixture_dir: str | None = None
    cache_dir: str | None = None
    output_root_dir: str = Field(min_length=1)
    data_version_prefix: str | None = None
    requires_network: bool
    requires_api_key: bool
    api_key_env_var: str | None = None
    enabled: bool
    notes: str | None = None

    @field_validator("source_name", "contract_source_name")
    @classmethod
    def normalize_source_names(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9_]+", normalized):
            raise ValueError("source_name must contain lowercase letters, digits, and underscores only")
        return normalized

    @field_validator("api_key_env_var")
    @classmethod
    def validate_api_key_env_var(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            raise ValueError("api_key_env_var must be an environment variable name, not a secret value")
        suspicious_parts = ("TOKEN", "SECRET", "KEY", "API")
        if not any(part in value for part in suspicious_parts):
            raise ValueError("api_key_env_var should name a secret environment variable")
        return value

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> SourceProfile:
        if self.mode == "offline_replay" and not self.fixture_dir:
            raise ValueError("offline_replay 模式必须配置 fixture_dir")
        if self.mode == "cache_only" and not self.cache_dir:
            raise ValueError("cache_only 模式必须配置 cache_dir")
        if self.requires_api_key and not self.api_key_env_var:
            raise ValueError("requires_api_key=true 时必须配置 api_key_env_var")
        return self


class MaterializationResult(RuntimeModel):
    source_name: str = Field(min_length=1)
    contract_source_name: str = Field(min_length=1)
    mode: SourceRuntimeMode
    output_dir: str
    data_version: str = Field(min_length=1)
    generated_files: list[str] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    contract_passed: bool
    validation_passed: bool
    quality_passed: bool | None = None
    status: MaterializationStatus
    error_message: str | None = None
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_status(self) -> MaterializationResult:
        if self.status == "SUCCESS" and self.error_message:
            raise ValueError("SUCCESS result must not include error_message")
        if self.status == "FAILED" and not self.error_message:
            raise ValueError("FAILED result must include error_message")
        return self
