from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from ashare_alpha.backtest.models import BacktestMetrics, BacktestResult, DailyEquityRecord, SimulatedTrade


def save_trades_csv(trades: list[SimulatedTrade], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(SimulatedTrade.__dataclass_fields__)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for trade in trades:
            writer.writerow(asdict(trade))


def save_daily_equity_csv(daily_equity: list[DailyEquityRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(DailyEquityRecord.__dataclass_fields__)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in daily_equity:
            writer.writerow(asdict(record))


def save_metrics_json(metrics: BacktestMetrics, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(metrics)
    payload["start_date"] = metrics.start_date.isoformat()
    payload["end_date"] = metrics.end_date.isoformat()
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_backtest_summary_md(result: BacktestResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics = result.metrics
    text = "\n".join(
        [
            "# Backtest Summary",
            "",
            "This is an offline research backtest. It does not place real orders or connect to brokers.",
            "",
            f"- Start date: {metrics.start_date.isoformat()}",
            f"- End date: {metrics.end_date.isoformat()}",
            f"- Initial cash: {metrics.initial_cash:.2f}",
            f"- Final equity: {metrics.final_equity:.2f}",
            f"- Total return: {metrics.total_return:.2%}",
            f"- Annualized return: {metrics.annualized_return:.2%}",
            f"- Max drawdown: {metrics.max_drawdown:.2%}",
            f"- Sharpe: {metrics.sharpe:.4f}",
            f"- Win rate: {metrics.win_rate:.2%}" if metrics.win_rate is not None else "- Win rate: N/A",
            f"- Turnover: {metrics.turnover:.4f}",
            f"- Trade count: {metrics.trade_count}",
            f"- Filled trades: {metrics.filled_trade_count}",
            f"- Rejected trades: {metrics.rejected_trade_count}",
        ]
    )
    output_path.write_text(text + "\n", encoding="utf-8")
