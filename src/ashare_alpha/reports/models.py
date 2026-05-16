from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


REPORT_DISCLAIMER = (
    "本报告仅用于量化研究和模拟复盘，不构成投资建议；回测和样例数据不代表未来表现，"
    "系统不会连接券商接口，也不会自动下单。"
)


class ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReportStockItem(ReportModel):
    ts_code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    industry: str | None = None
    signal: str = Field(min_length=1)
    stock_score: float = Field(ge=0, le=100)
    risk_level: str = Field(min_length=1)
    target_weight: float = Field(ge=0, le=1)
    target_shares: int = Field(ge=0)
    estimated_position_value: float = Field(ge=0)
    latest_close: float | None = None
    liquidity_score: float | None = None
    event_score: float | None = None
    event_risk_score: float | None = None
    reason: str = Field(min_length=1)
    buy_reasons: list[str] = Field(default_factory=list)
    risk_reasons: list[str] = Field(default_factory=list)
    universe_exclude_reason_text: str | None = None
    event_reason: str | None = None


class DailyResearchReport(ReportModel):
    report_date: date
    generated_at: datetime
    data_dir: str
    config_dir: str

    total_stocks: int = Field(ge=0)
    allowed_universe_count: int = Field(ge=0)
    blocked_universe_count: int = Field(ge=0)
    buy_count: int = Field(ge=0)
    watch_count: int = Field(ge=0)
    block_count: int = Field(ge=0)
    high_risk_count: int = Field(ge=0)
    market_regime: str
    market_regime_score: float = Field(ge=0, le=100)

    buy_candidates: list[ReportStockItem] = Field(default_factory=list)
    watch_candidates: list[ReportStockItem] = Field(default_factory=list)
    blocked_stocks: list[ReportStockItem] = Field(default_factory=list)
    high_risk_stocks: list[ReportStockItem] = Field(default_factory=list)
    recent_event_risk_stocks: list[ReportStockItem] = Field(default_factory=list)

    universe_exclude_reason_counts: dict[str, int] = Field(default_factory=dict)
    signal_reason_counts: dict[str, int] = Field(default_factory=dict)
    event_block_buy_count: int = Field(ge=0)
    event_high_risk_count: int = Field(ge=0)
    average_stock_score: float | None = None
    average_risk_score: float | None = None

    initial_cash: float = Field(gt=0)
    max_positions: int = Field(ge=1)
    max_position_weight: float = Field(gt=0, le=1)
    lot_size: int = Field(gt=0)
    commission_rate: float = Field(ge=0)
    min_commission: float = Field(ge=0)
    stamp_tax_rate_on_sell: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)

    disclaimer: str = REPORT_DISCLAIMER


class BacktestSymbolSummary(ReportModel):
    ts_code: str = Field(min_length=1)
    filled_trades: int = Field(ge=0)
    buy_count: int = Field(ge=0)
    sell_count: int = Field(ge=0)
    realized_pnl: float
    rejected_trades: int = Field(ge=0)


class BacktestResearchReport(ReportModel):
    start_date: date
    end_date: date
    generated_at: datetime
    output_dir: str

    initial_cash: float = Field(gt=0)
    final_equity: float = Field(ge=0)
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe: float
    win_rate: float | None
    turnover: float
    trade_count: int = Field(ge=0)
    filled_trade_count: int = Field(ge=0)
    rejected_trade_count: int = Field(ge=0)
    average_holding_days: float | None
    price_source: str = "raw"
    execution_price_source: str = "raw"
    valuation_price_source: str = "raw"
    adjusted_research_note: str = (
        "Adjusted valuation is for research only; execution constraints remain based on raw daily bars."
    )

    no_trade: bool
    no_trade_reason: str | None = None
    top_reject_reasons: dict[str, int] = Field(default_factory=dict)
    trade_summary_by_symbol: list[BacktestSymbolSummary] = Field(default_factory=list)
    equity_curve_tail: list[dict[str, Any]] = Field(default_factory=list)

    initial_cash_config: float = Field(gt=0)
    max_positions: int = Field(ge=1)
    max_position_weight: float = Field(gt=0, le=1)
    rebalance_frequency: str
    execution_price: str
    t_plus_one: bool
    lot_size: int = Field(gt=0)
    commission_rate: float = Field(ge=0)
    min_commission: float = Field(ge=0)
    stamp_tax_rate_on_sell: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)

    disclaimer: str = REPORT_DISCLAIMER
