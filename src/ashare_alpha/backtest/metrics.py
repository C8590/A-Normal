from __future__ import annotations

import math

from ashare_alpha.backtest.models import BacktestMetrics, DailyEquityRecord, SimulatedTrade


def calculate_metrics(
    daily_equity: list[DailyEquityRecord],
    trades: list[SimulatedTrade],
    initial_cash: float,
    annualization_days: int,
) -> BacktestMetrics:
    if not daily_equity:
        raise ValueError("daily_equity must not be empty")
    final_equity = daily_equity[-1].total_equity
    total_return = final_equity / initial_cash - 1 if initial_cash > 0 else 0.0
    n_days = len(daily_equity)
    annualized_return = (1 + total_return) ** (annualization_days / (n_days - 1)) - 1 if n_days > 1 else 0.0
    max_drawdown = min(record.drawdown for record in daily_equity)
    sharpe = _sharpe([record.daily_return for record in daily_equity[1:]], annualization_days)
    sell_pnls = [trade.realized_pnl for trade in trades if trade.status == "FILLED" and trade.side == "SELL" and trade.realized_pnl is not None]
    win_rate = None if not sell_pnls else sum(1 for pnl in sell_pnls if pnl > 0) / len(sell_pnls)
    average_equity = sum(record.total_equity for record in daily_equity) / len(daily_equity)
    turnover = (
        sum(abs(trade.gross_value) for trade in trades if trade.status == "FILLED") / average_equity
        if average_equity > 0
        else 0.0
    )
    holding_days = [trade.holding_days for trade in trades if trade.status == "FILLED" and trade.side == "SELL" and trade.holding_days is not None]
    average_holding_days = None if not holding_days else sum(holding_days) / len(holding_days)
    return BacktestMetrics(
        start_date=daily_equity[0].trade_date,
        end_date=daily_equity[-1].trade_date,
        initial_cash=initial_cash,
        final_equity=final_equity,
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        sharpe=sharpe,
        win_rate=win_rate,
        turnover=turnover,
        trade_count=len(trades),
        filled_trade_count=sum(1 for trade in trades if trade.status == "FILLED"),
        rejected_trade_count=sum(1 for trade in trades if trade.status == "REJECTED"),
        average_holding_days=average_holding_days,
    )


def _sharpe(returns: list[float], annualization_days: int) -> float:
    if not returns:
        return 0.0
    mean_return = sum(returns) / len(returns)
    variance = sum((value - mean_return) ** 2 for value in returns) / len(returns)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return mean_return / std * math.sqrt(annualization_days)
