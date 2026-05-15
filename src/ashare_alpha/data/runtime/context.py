from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ashare_alpha.data.runtime.models import SourceProfile
from ashare_alpha.security import EnvSecretProvider, NetworkGuard, SecurityConfig


class SourceRuntimeError(RuntimeError):
    """Raised when a source runtime profile cannot be executed safely."""


@dataclass(frozen=True)
class SourceRuntimeContext:
    profile: SourceProfile
    security_config: SecurityConfig
    network_guard: NetworkGuard
    secret_provider: EnvSecretProvider
    created_at: datetime = field(default_factory=datetime.now)

    def assert_can_run_offline(self) -> None:
        if not self.profile.enabled:
            raise SourceRuntimeError(f"数据源 profile 已禁用，不能运行：{self.profile.source_name}")
        if self.profile.mode == "live_disabled":
            raise SourceRuntimeError(f"live_disabled 只是联网占位模式，当前不能运行：{self.profile.source_name}")
        if self.profile.mode not in {"offline_replay", "cache_only"}:
            raise SourceRuntimeError(f"不支持的数据源运行模式：{self.profile.mode}")
        if self.profile.requires_network:
            self.assert_can_attempt_network()
        if self.profile.requires_api_key and self.profile.api_key_env_var:
            self.secret_provider.require_secret(self.profile.api_key_env_var)

    def assert_can_attempt_network(self, domain: str | None = None) -> None:
        if self.profile.mode == "live_disabled":
            raise SourceRuntimeError(f"live_disabled 模式不能发起网络访问：{self.profile.source_name}")
        try:
            self.network_guard.assert_network_allowed(self.profile.source_name, domain)
        except RuntimeError as exc:
            raise SourceRuntimeError(
                f"当前安全配置禁止数据源 {self.profile.source_name} 联网；"
                "真实网络入口必须先通过 NetworkGuard。"
            ) from exc
