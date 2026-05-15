from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ashare_alpha.config import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    ConfigYamlError,
    load_project_config,
)
from a_normal.config import FeesConfig, TradingRulesConfig, load_config


ASHARE_ALPHA_VALID_CONFIG_DIR = Path("tests/fixtures/configs/valid")


def write_yaml(path, payload):
    path.write_text(yaml.safe_dump(payload, sort_keys=True), encoding="utf-8")


def copy_ashare_alpha_config(tmp_path):
    config_dir = tmp_path / "ashare_alpha_config"
    shutil.copytree(ASHARE_ALPHA_VALID_CONFIG_DIR, config_dir)
    return config_dir


def test_load_config_reads_default_configs():
    config = load_config()

    assert config.trading_rules.lot_size == 100
    assert config.trading_rules.price_tick == 0.01
    assert config.trading_rules.t_plus_one is True
    assert config.trading_rules.normal_limit_pct == 0.10
    assert config.trading_rules.st_limit_pct == 0.05
    assert config.fees.commission_rate == 0.00005
    assert config.fees.min_commission == 0.1
    assert config.fees.stamp_tax_rate_on_sell == 0.0005


def test_load_config_uses_schema_defaults_for_missing_fields(tmp_path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    write_yaml(config_dir / "trading_rules.yaml", {"lot_size": 200})
    write_yaml(config_dir / "fees.yaml", {"stamp_tax_rate_on_sell": 0.001})

    config = load_config(config_dir)

    assert config.trading_rules == TradingRulesConfig(lot_size=200)
    assert config.fees == FeesConfig(stamp_tax_rate_on_sell=0.001)


def test_load_config_rejects_invalid_values(tmp_path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    write_yaml(config_dir / "trading_rules.yaml", {"lot_size": 0})

    with pytest.raises(ValidationError):
        load_config(config_dir)


def test_ashare_alpha_default_config_loads():
    config = load_project_config()

    assert config.trading_rules.lot_size == 100
    assert config.trading_rules.price_tick == 0.01
    assert config.fees.stamp_tax_rate_on_sell == 0.0005
    assert config.scoring.thresholds.buy > config.scoring.thresholds.watch
    assert abs(sum(config.scoring.weights.values()) - 1.0) <= 1e-6


def test_ashare_alpha_explicit_config_dir_loads():
    config = load_project_config(ASHARE_ALPHA_VALID_CONFIG_DIR)

    assert config.universe.allowed_boards == ("main",)
    assert config.backtest.rebalance_frequency == "weekly"


def test_ashare_alpha_missing_config_file_raises_clear_error(tmp_path):
    config_dir = copy_ashare_alpha_config(tmp_path)
    (config_dir / "fees.yaml").unlink()

    with pytest.raises(ConfigFileNotFoundError, match="Missing config file"):
        load_project_config(config_dir)


def test_ashare_alpha_invalid_yaml_raises_clear_error(tmp_path):
    config_dir = copy_ashare_alpha_config(tmp_path)
    (config_dir / "fees.yaml").write_text("commission_rate: [\n", encoding="utf-8")

    with pytest.raises(ConfigYamlError, match="Invalid YAML"):
        load_project_config(config_dir)


def test_ashare_alpha_negative_commission_rate_is_rejected(tmp_path):
    config_dir = copy_ashare_alpha_config(tmp_path)
    write_yaml(
        config_dir / "fees.yaml",
        {
            "commission_rate": -0.00005,
            "min_commission": 0.1,
            "stamp_tax_rate_on_sell": 0.0005,
            "transfer_fee_rate": 0.0,
            "slippage_bps": 5,
        },
    )

    with pytest.raises(ConfigValidationError, match="commission_rate"):
        load_project_config(config_dir)


def test_ashare_alpha_zero_price_tick_is_rejected(tmp_path):
    config_dir = copy_ashare_alpha_config(tmp_path)
    write_yaml(
        config_dir / "trading_rules.yaml",
        {
            "lot_size": 100,
            "price_tick": 0,
            "t_plus_one": True,
            "normal_limit_pct": 0.10,
            "st_limit_pct": 0.05,
            "block_buy_at_limit_up": True,
            "block_sell_at_limit_down": True,
            "allow_short_selling": False,
            "allow_margin_trading": False,
        },
    )

    with pytest.raises(ConfigValidationError, match="price_tick"):
        load_project_config(config_dir)


def test_ashare_alpha_scoring_weights_must_sum_to_one(tmp_path):
    config_dir = copy_ashare_alpha_config(tmp_path)
    scoring = yaml.safe_load((config_dir / "scoring.yaml").read_text(encoding="utf-8"))
    scoring["weights"]["market_regime"] = 0.10
    write_yaml(config_dir / "scoring.yaml", scoring)

    with pytest.raises(ConfigValidationError, match="weights must sum"):
        load_project_config(config_dir)


def test_ashare_alpha_buy_threshold_must_exceed_watch_threshold(tmp_path):
    config_dir = copy_ashare_alpha_config(tmp_path)
    scoring = yaml.safe_load((config_dir / "scoring.yaml").read_text(encoding="utf-8"))
    scoring["thresholds"]["buy"] = 60
    scoring["thresholds"]["watch"] = 65
    write_yaml(config_dir / "scoring.yaml", scoring)

    with pytest.raises(ConfigValidationError, match="buy threshold"):
        load_project_config(config_dir)


def test_ashare_alpha_show_config_cli_runs():
    result = subprocess.run(
        [sys.executable, "-m", "ashare_alpha", "show-config"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"trading_rules"' in result.stdout
    assert '"stamp_tax_rate_on_sell": 0.0005' in result.stdout


def test_ashare_alpha_show_config_cli_accepts_config_dir():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ashare_alpha",
            "show-config",
            "--config-dir",
            str(ASHARE_ALPHA_VALID_CONFIG_DIR),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"rebalance_frequency": "weekly"' in result.stdout


def test_load_config_rejects_unknown_fields(tmp_path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    write_yaml(config_dir / "fees.yaml", {"commission_rate": 0.00005, "hidden_fee": 1})

    with pytest.raises(ValidationError):
        load_config(config_dir)
