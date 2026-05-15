from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"


class TradingRulesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    lot_size: int = Field(default=100, gt=0)
    price_tick: float = Field(default=0.01, gt=0)
    t_plus_one: bool = True
    normal_limit_pct: float = Field(default=0.10, gt=0, le=1)
    st_limit_pct: float = Field(default=0.05, gt=0, le=1)


class FeesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    commission_rate: float = Field(default=0.00005, ge=0)
    min_commission: float = Field(default=0.1, ge=0)
    stamp_tax_rate_on_sell: float = Field(default=0.0005, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)


class UniverseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allowed_exchanges: tuple[str, ...] = ("SSE", "SZSE")
    mainboard_prefixes: dict[str, tuple[str, ...]] = Field(
        default_factory=lambda: {
            "SSE": ("600", "601", "603", "605"),
            "SZSE": ("000", "001", "002", "003"),
        }
    )
    min_listing_trading_days: int = Field(default=120, ge=0)
    liquidity_lookback_days: int = Field(default=20, gt=0)
    min_avg_amount_20d: float = Field(default=10_000_000.0, ge=0)
    initial_capital: float = Field(default=10_000.0, gt=0)
    lot_size: int = Field(default=100, gt=0)
    max_position_pct_for_entry: float = Field(default=1.0, gt=0, le=1)
    negative_event_lookback_days: int = Field(default=30, ge=0)
    negative_event_categories: tuple[str, ...] = (
        "regulatory_penalty",
        "investigation",
        "lawsuit",
        "earnings_warning",
    )
    negative_event_keywords: tuple[str, ...] = (
        "penalty",
        "investigation",
        "lawsuit",
        "loss warning",
        "regulatory",
    )
    delisting_risk_keywords: tuple[str, ...] = ("delisting risk", "退市风险", "终止上市")


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trading_rules: TradingRulesConfig = Field(default_factory=TradingRulesConfig)
    fees: FeesConfig = Field(default_factory=FeesConfig)
    universe: UniverseConfig = Field(default_factory=UniverseConfig)


Config = AppConfig
TradingRules = TradingRulesConfig
Fees = FeesConfig
Universe = UniverseConfig


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise TypeError(f"YAML config must contain a mapping: {path}")
    return raw


def load_config(config_dir: str | Path | None = None) -> AppConfig:
    """Load and validate YAML configuration from a configs directory.

    The loader reads ``trading_rules.yaml`` and ``fees.yaml`` from ``config_dir``.
    Missing files or missing fields fall back to the schema defaults, while
    invalid values and unknown keys are rejected by pydantic.
    """

    base_dir = Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR
    raw_config = {
        "trading_rules": _read_yaml(base_dir / "trading_rules.yaml"),
        "fees": _read_yaml(base_dir / "fees.yaml"),
        "universe": _read_yaml(base_dir / "universe.yaml"),
    }
    return AppConfig.model_validate(raw_config)
