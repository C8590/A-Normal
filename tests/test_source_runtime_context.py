from __future__ import annotations

import pytest

from ashare_alpha.data.runtime import SourceProfile, SourceRuntimeContext
from ashare_alpha.data.runtime.context import SourceRuntimeError
from ashare_alpha.security import EnvSecretProvider, NetworkGuard, SecurityConfig
from ashare_alpha.security.models import NetworkPolicyConfig, SecretPolicyConfig


def test_offline_replay_can_run_in_offline_mode() -> None:
    _context(_profile()).assert_can_run_offline()


def test_cache_only_can_run_in_offline_mode() -> None:
    _context(_profile(mode="cache_only")).assert_can_run_offline()


def test_requires_network_is_blocked_by_network_guard() -> None:
    with pytest.raises(SourceRuntimeError, match="禁止.*联网"):
        _context(_profile(requires_network=True)).assert_can_attempt_network()


def test_live_disabled_raises_clear_error() -> None:
    with pytest.raises(SourceRuntimeError, match="live_disabled"):
        _context(_profile(mode="live_disabled")).assert_can_run_offline()


def _context(profile: SourceProfile) -> SourceRuntimeContext:
    security = _security()
    return SourceRuntimeContext(
        profile=profile,
        security_config=security,
        network_guard=NetworkGuard(security),
        secret_provider=EnvSecretProvider(),
    )


def _profile(mode: str = "offline_replay", requires_network: bool = False) -> SourceProfile:
    return SourceProfile.model_validate(
        {
            "source_name": "example_offline",
            "display_name": "Example Offline",
            "mode": mode,
            "contract_source_name": "tushare_like",
            "mapping_path": "configs/ashare_alpha/data_sources/tushare_like_mapping.yaml",
            "fixture_dir": "tests/fixtures/external_sources/tushare_like" if mode == "offline_replay" else None,
            "cache_dir": "data/sample/ashare_alpha" if mode == "cache_only" else "data/cache/external/example",
            "output_root_dir": "data/materialized",
            "data_version_prefix": "example",
            "requires_network": requires_network,
            "requires_api_key": False,
            "api_key_env_var": None,
            "enabled": True,
            "notes": None,
        }
    )


def _security() -> SecurityConfig:
    return SecurityConfig(
        offline_mode=True,
        allow_network=False,
        allow_broker_connections=False,
        allow_live_trading=False,
        secret_policy=SecretPolicyConfig(),
        network_policy=NetworkPolicyConfig(
            require_explicit_enable=True,
            allowed_domains=[],
            default_timeout_seconds=10,
            max_retries=0,
        ),
        data_sources={},
    )
