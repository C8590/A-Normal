from __future__ import annotations

import pytest
from pydantic import ValidationError

from ashare_alpha.data.runtime import SourceProfile


def test_source_profile_offline_replay_valid() -> None:
    profile = _profile()

    assert profile.source_name == "tushare_like_offline"
    assert profile.mode == "offline_replay"


def test_offline_replay_requires_fixture_dir() -> None:
    with pytest.raises(ValidationError, match="fixture_dir"):
        SourceProfile.model_validate({**_payload(), "fixture_dir": None})


def test_cache_only_requires_cache_dir() -> None:
    with pytest.raises(ValidationError, match="cache_dir"):
        SourceProfile.model_validate({**_payload(), "mode": "cache_only", "cache_dir": None})


def test_live_disabled_profile_can_be_declared_but_not_run() -> None:
    profile = SourceProfile.model_validate({**_payload(), "mode": "live_disabled", "fixture_dir": None})

    assert profile.mode == "live_disabled"


def test_api_key_env_var_must_not_be_secret_value() -> None:
    with pytest.raises(ValidationError, match="environment variable name"):
        SourceProfile.model_validate(
            {
                **_payload(),
                "requires_api_key": True,
                "api_key_env_var": "plain-secret-value-123",
            }
        )


def _profile() -> SourceProfile:
    return SourceProfile.model_validate(_payload())


def _payload() -> dict[str, object]:
    return {
        "source_name": "tushare_like_offline",
        "display_name": "Tushare-like Offline Replay",
        "mode": "offline_replay",
        "contract_source_name": "tushare_like",
        "mapping_path": "configs/ashare_alpha/data_sources/tushare_like_mapping.yaml",
        "fixture_dir": "tests/fixtures/external_sources/tushare_like",
        "cache_dir": "data/cache/external/tushare_like",
        "output_root_dir": "data/materialized",
        "data_version_prefix": "tushare_like",
        "requires_network": False,
        "requires_api_key": False,
        "api_key_env_var": None,
        "enabled": True,
        "notes": "offline",
    }
