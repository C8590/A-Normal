from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class TradeCost:
    gross_value: float
    commission: float
    stamp_tax: float
    transfer_fee: float
    total_fee: float
    net_cash_change: float


@dataclass(frozen=True)
class SimulatedOrder:
    decision_date: date
    execution_date: date
    ts_code: str
    side: str
    requested_shares: int
    target_weight: float
    reason: str

    def __post_init__(self) -> None:
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if self.requested_shares <= 0:
            raise ValueError("requested_shares must be greater than 0")
        if not 0 <= self.target_weight <= 1:
            raise ValueError("target_weight must be between 0 and 1")
        if not self.reason:
            raise ValueError("reason must not be empty")


@dataclass(frozen=True)
class SimulatedTrade:
    decision_date: date
    execution_date: date
    ts_code: str
    side: str
    requested_shares: int
    filled_shares: int
    price: float | None
    gross_value: float
    commission: float
    stamp_tax: float
    transfer_fee: float
    total_fee: float
    net_cash_change: float
    status: str
    reject_reason: str | None
    realized_pnl: float | None
    holding_days: int | None
    reason: str

    def __post_init__(self) -> None:
        if self.status not in {"FILLED", "REJECTED", "PARTIAL"}:
            raise ValueError("status must be FILLED, REJECTED, or PARTIAL")


@dataclass
class PositionLot:
    ts_code: str
    shares: int
    cost_per_share: float
    buy_date: date


@dataclass(frozen=True)
class PositionSnapshot:
    trade_date: date
    ts_code: str
    shares: int
    available_shares: int
    market_price: float | None
    market_value: float
    average_cost: float | None
    unrealized_pnl: float | None


@dataclass(frozen=True)
class DailyEquityRecord:
    trade_date: date
    cash: float
    market_value: float
    total_equity: float
    positions_count: int
    gross_exposure: float
    daily_return: float
    drawdown: float


@dataclass(frozen=True)
class BacktestMetrics:
    start_date: date
    end_date: date
    initial_cash: float
    final_equity: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe: float
    win_rate: float | None
    turnover: float
    trade_count: int
    filled_trade_count: int
    rejected_trade_count: int
    average_holding_days: float | None


@dataclass(frozen=True)
class BacktestResult:
    metrics: BacktestMetrics
    trades: list[SimulatedTrade] = field(default_factory=list)
    daily_equity: list[DailyEquityRecord] = field(default_factory=list)
