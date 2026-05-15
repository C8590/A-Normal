from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from ashare_alpha.config import ConfigValidationError, load_project_config


VALID_CONFIG_DIR = Path("tests/fixtures/configs/valid")


def test_security_yaml_default_loads() -> None:
    config = load_project_config()

    assert config.security.offline_mode is True
    assert config.security.allow_network is False
    assert config.security.data_sources["local_csv"].enabled is True


def test_offline_mode_true_with_allow_network_true_is_rejected(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    security = _read_security(config_dir)
    security["allow_network"] = True
    _write_security(config_dir, security)

    with pytest.raises(ConfigValidationError, match="offline_mode"):
        load_project_config(config_dir)


def test_live_trading_requires_broker_connections(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    security = _read_security(config_dir)
    security["allow_live_trading"] = True
    security["allow_broker_connections"] = False
    _write_security(config_dir, security)

    with pytest.raises(ConfigValidationError, match="allow_live_trading"):
        load_project_config(config_dir)


def test_requires_api_key_requires_env_var(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    security = _read_security(config_dir)
    security["data_sources"]["tushare_stub"]["api_key_env_var"] = None
    _write_security(config_dir, security)

    with pytest.raises(ConfigValidationError, match="api_key_env_var"):
        load_project_config(config_dir)


def test_api_key_env_var_prefix_must_be_allowed(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    security = _read_security(config_dir)
    security["data_sources"]["tushare_stub"]["api_key_env_var"] = "BAD_PREFIX_TOKEN"
    _write_security(config_dir, security)

    with pytest.raises(ConfigValidationError, match="must start"):
        load_project_config(config_dir)


def test_show_config_does_not_output_real_env_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASHARE_ALPHA_TUSHARE_TOKEN", "secret-value-never-print")
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "show-config"],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": "src"},
    )

    assert result.returncode == 0
    assert "secret-value-never-print" not in result.stdout


def _copy_config(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    shutil.copytree(VALID_CONFIG_DIR, config_dir)
    return config_dir


def _read_security(config_dir: Path) -> dict:
    return yaml.safe_load((config_dir / "security.yaml").read_text(encoding="utf-8"))


def _write_security(config_dir: Path, payload: dict) -> None:
    (config_dir / "security.yaml").write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")
