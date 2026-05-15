from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SecurityIssueSeverity = Literal["info", "warning", "error"]


class SecurityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class SecretPolicyConfig(SecurityModel):
    allow_plaintext_secrets_in_config: bool = False
    allowed_secret_env_prefixes: list[str] = Field(default_factory=lambda: ["ASHARE_ALPHA_"])
    required_redaction: bool = True

    @field_validator("allowed_secret_env_prefixes")
    @classmethod
    def validate_prefixes(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("allowed_secret_env_prefixes must not be empty")
        for prefix in value:
            if not re.fullmatch(r"[A-Z0-9_]+", prefix):
                raise ValueError("allowed_secret_env_prefixes must contain uppercase letters, digits, and underscores only")
        return value


class NetworkPolicyConfig(SecurityModel):
    require_explicit_enable: bool = True
    allowed_domains: list[str] = Field(default_factory=list)
    default_timeout_seconds: int = Field(gt=0)
    max_retries: int = Field(ge=0)


class DataSourceSecurityConfig(SecurityModel):
    enabled: bool
    requires_network: bool
    requires_api_key: bool
    api_key_env_var: str | None = None

    @field_validator("api_key_env_var")
    @classmethod
    def validate_env_var_shape(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        if not re.fullmatch(r"[A-Z0-9_]+", value):
            raise ValueError("api_key_env_var must contain uppercase letters, digits, and underscores only")
        return value

    @model_validator(mode="after")
    def require_api_key_env_var(self) -> DataSourceSecurityConfig:
        if self.requires_api_key and not self.api_key_env_var:
            raise ValueError("api_key_env_var is required when requires_api_key is true")
        return self


class SecurityConfig(SecurityModel):
    offline_mode: bool
    allow_network: bool
    allow_broker_connections: bool
    allow_live_trading: bool
    secret_policy: SecretPolicyConfig
    network_policy: NetworkPolicyConfig
    data_sources: dict[str, DataSourceSecurityConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_security_policy(self) -> SecurityConfig:
        if self.allow_live_trading and not self.allow_broker_connections:
            raise ValueError("allow_live_trading=true requires allow_broker_connections=true")
        if self.offline_mode and self.allow_network:
            raise ValueError("offline_mode=true requires allow_network=false")
        prefixes = tuple(self.secret_policy.allowed_secret_env_prefixes)
        for source_name, data_source in self.data_sources.items():
            env_var = data_source.api_key_env_var
            if env_var and not env_var.startswith(prefixes):
                raise ValueError(
                    f"data_sources.{source_name}.api_key_env_var must start with one of: {', '.join(prefixes)}"
                )
        return self


class SecurityScanIssue(SecurityModel):
    severity: SecurityIssueSeverity
    file_path: str
    key_path: str | None = None
    issue_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class SecurityScanReport(SecurityModel):
    generated_at: datetime
    config_dir: str
    total_issues: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    passed: bool
    issues: list[SecurityScanIssue] = Field(default_factory=list)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_counts(self) -> SecurityScanReport:
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
