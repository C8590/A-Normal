from __future__ import annotations

import pytest

from ashare_alpha.security import (
    BrokerConnectionDisabledError,
    DomainNotAllowedError,
    LiveTradingDisabledError,
    NetworkDisabledError,
    NetworkGuard,
    NetworkPolicyConfig,
    SecretPolicyConfig,
    SecurityConfig,
)


def test_offline_mode_blocks_network() -> None:
    guard = NetworkGuard(_security(offline_mode=True, allow_network=False))

    with pytest.raises(NetworkDisabledError):
        guard.assert_network_allowed("tushare_stub")


def test_allow_network_false_blocks_network() -> None:
    guard = NetworkGuard(_security(offline_mode=False, allow_network=False))

    with pytest.raises(NetworkDisabledError):
        guard.assert_network_allowed("tushare_stub")


def test_domain_not_in_allowlist_is_blocked() -> None:
    guard = NetworkGuard(_security(offline_mode=False, allow_network=True, allowed_domains=["example.com"]))

    with pytest.raises(DomainNotAllowedError):
        guard.assert_network_allowed("tushare_stub", "blocked.example")


def test_broker_connection_disabled_blocks_broker_connection() -> None:
    guard = NetworkGuard(_security(allow_broker_connections=False))

    with pytest.raises(BrokerConnectionDisabledError):
        guard.assert_broker_connection_allowed()


def test_live_trading_disabled_blocks_live_trading() -> None:
    guard = NetworkGuard(_security(allow_live_trading=False))

    with pytest.raises(LiveTradingDisabledError):
        guard.assert_live_trading_allowed()


def test_network_allowed_with_allowlisted_domain() -> None:
    guard = NetworkGuard(_security(offline_mode=False, allow_network=True, allowed_domains=["example.com"]))

    guard.assert_network_allowed("future_source", "example.com")


def _security(
    offline_mode: bool = True,
    allow_network: bool = False,
    allow_broker_connections: bool = False,
    allow_live_trading: bool = False,
    allowed_domains: list[str] | None = None,
) -> SecurityConfig:
    return SecurityConfig(
        offline_mode=offline_mode,
        allow_network=allow_network,
        allow_broker_connections=allow_broker_connections,
        allow_live_trading=allow_live_trading,
        secret_policy=SecretPolicyConfig(
            allow_plaintext_secrets_in_config=False,
            allowed_secret_env_prefixes=["ASHARE_ALPHA_"],
            required_redaction=True,
        ),
        network_policy=NetworkPolicyConfig(
            require_explicit_enable=True,
            allowed_domains=allowed_domains or [],
            default_timeout_seconds=10,
            max_retries=0,
        ),
        data_sources={},
    )
