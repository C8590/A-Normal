from __future__ import annotations

from ashare_alpha.backtest.broker_simulator import BrokerSimulator
from ashare_alpha.backtest.cost_model import CostModel
from ashare_alpha.backtest.engine import BacktestEngine, get_trading_dates, select_rebalance_dates
from ashare_alpha.backtest.metrics import calculate_metrics
from ashare_alpha.backtest.models import (
    BacktestMetrics,
    BacktestResult,
    DailyEquityRecord,
    PositionLot,
    PositionSnapshot,
    SimulatedOrder,
    SimulatedTrade,
    TradeCost,
)
from ashare_alpha.backtest.portfolio import Portfolio
from ashare_alpha.backtest.price_source import BacktestPriceSourceProvider
from ashare_alpha.backtest.storage import (
    save_backtest_summary_md,
    save_daily_equity_csv,
    save_metrics_json,
    save_trades_csv,
)

__all__ = [
    "BacktestEngine",
    "BacktestMetrics",
    "BacktestResult",
    "BacktestPriceSourceProvider",
    "BrokerSimulator",
    "CostModel",
    "DailyEquityRecord",
    "Portfolio",
    "PositionLot",
    "PositionSnapshot",
    "SimulatedOrder",
    "SimulatedTrade",
    "TradeCost",
    "calculate_metrics",
    "get_trading_dates",
    "save_backtest_summary_md",
    "save_daily_equity_csv",
    "save_metrics_json",
    "save_trades_csv",
    "select_rebalance_dates",
]
