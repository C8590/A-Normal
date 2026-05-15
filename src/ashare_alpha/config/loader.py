from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError
from yaml import YAMLError

from ashare_alpha.config.errors import ConfigFileNotFoundError, ConfigValidationError, ConfigYamlError
from ashare_alpha.config.schema import ProjectConfig


DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[3] / "configs" / "ashare_alpha"

CONFIG_FILES = {
    "universe": "universe.yaml",
    "trading_rules": "trading_rules.yaml",
    "fees": "fees.yaml",
    "factors": "factors.yaml",
    "scoring": "scoring.yaml",
    "backtest": "backtest.yaml",
    "probability": "probability.yaml",
    "security": "security.yaml",
}


def load_yaml_config(path: Path) -> dict[str, Any]:
    """Load one YAML config file and require a mapping at the top level."""

    if not path.exists():
        raise ConfigFileNotFoundError(f"Missing config file: {path}")

    try:
        with path.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream)
    except YAMLError as exc:
        raise ConfigYamlError(f"Invalid YAML in config file {path}: {exc}") from exc

    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ConfigYamlError(f"Config file must contain a YAML mapping: {path}")
    return data


def load_project_config(config_dir: Path | None = None) -> ProjectConfig:
    """Load and validate the full project configuration set."""

    base_dir = config_dir or DEFAULT_CONFIG_DIR
    raw_config = {section: load_yaml_config(base_dir / filename) for section, filename in CONFIG_FILES.items()}

    try:
        return ProjectConfig.model_validate(raw_config)
    except ValidationError as exc:
        raise ConfigValidationError(f"Invalid project config in {base_dir}: {exc}") from exc
