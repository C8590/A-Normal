from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from ashare_alpha.config import ConfigValidationError, load_project_config


VALID_CONFIG_DIR = Path("tests/fixtures/configs/valid")


def test_probability_yaml_default_config_loads() -> None:
    config = load_project_config()

    assert config.probability.horizons == (5, 10, 20)
    assert config.probability.score_field == "stock_score"


def test_probability_horizons_empty_rejected(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    probability = yaml.safe_load((config_dir / "probability.yaml").read_text(encoding="utf-8"))
    probability["horizons"] = []
    _write_yaml(config_dir / "probability.yaml", probability)

    with pytest.raises(ConfigValidationError, match="horizons"):
        load_project_config(config_dir)


def test_probability_n_bins_less_than_two_rejected(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    probability = yaml.safe_load((config_dir / "probability.yaml").read_text(encoding="utf-8"))
    probability["n_bins"] = 1
    _write_yaml(config_dir / "probability.yaml", probability)

    with pytest.raises(ConfigValidationError, match="n_bins"):
        load_project_config(config_dir)


def test_probability_split_ratio_invalid_rejected(tmp_path: Path) -> None:
    config_dir = _copy_config(tmp_path)
    probability = yaml.safe_load((config_dir / "probability.yaml").read_text(encoding="utf-8"))
    probability["train_test_split_ratio"] = 1.0
    _write_yaml(config_dir / "probability.yaml", probability)

    with pytest.raises(ConfigValidationError, match="train_test_split_ratio"):
        load_project_config(config_dir)


def _copy_config(tmp_path: Path) -> Path:
    config_dir = tmp_path / "configs"
    shutil.copytree(VALID_CONFIG_DIR, config_dir)
    return config_dir


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
