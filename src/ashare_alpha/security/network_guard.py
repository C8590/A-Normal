from __future__ import annotations

from ashare_alpha.security.models import SecurityConfig


class NetworkDisabledError(RuntimeError):
    """Raised when network access is disabled by policy."""


class DomainNotAllowedError(RuntimeError):
    """Raised when a requested network domain is outside the allow-list."""


class BrokerConnectionDisabledError(RuntimeError):
    """Raised when broker connections are disabled by policy."""


class LiveTradingDisabledError(RuntimeError):
    """Raised when live trading is disabled by policy."""


class NetworkGuard:
    def __init__(self, security_config: SecurityConfig) -> None:
        self.security_config = security_config

    def assert_network_allowed(self, source_name: str, domain: str | None = None) -> None:
        if self.security_config.offline_mode:
            raise NetworkDisabledError(f"当前处于离线模式，禁止数据源 {source_name} 发起网络访问。")
        if not self.security_config.allow_network:
            raise NetworkDisabledError(f"安全配置未允许联网，禁止数据源 {source_name} 发起网络访问。")
        allowed_domains = self.security_config.network_policy.allowed_domains
        if domain is not None and allowed_domains and domain not in allowed_domains:
            raise DomainNotAllowedError(f"域名 {domain} 不在安全白名单中，数据源 {source_name} 不允许访问。")

    def assert_broker_connection_allowed(self) -> None:
        if not self.security_config.allow_broker_connections:
            raise BrokerConnectionDisabledError("安全配置禁止券商连接。")

    def assert_live_trading_allowed(self) -> None:
        if not self.security_config.allow_live_trading:
            raise LiveTradingDisabledError("安全配置禁止实盘交易。")
