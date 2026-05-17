from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError
from yaml import YAMLError

from ashare_alpha.gates.models import ResearchQualityGateConfig


DEFAULT_GATE_CONFIG_PATH = Path("configs/ashare_alpha/gates/research_quality_gates.yaml")


def load_research_quality_gate_config(path: Path = DEFAULT_GATE_CONFIG_PATH) -> ResearchQualityGateConfig:
    if not Path(path).exists():
        raise ValueError(f"research quality gates config not found: {path}")
    try:
        payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except YAMLError as exc:
        raise ValueError(f"invalid research quality gates YAML: {path}: {exc}") from exc
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ValueError(f"research quality gates config must be a mapping: {path}")
    try:
        return ResearchQualityGateConfig.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"invalid research quality gates config: {path}: {exc}") from exc
