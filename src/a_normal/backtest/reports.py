from __future__ import annotations

import csv
from pathlib import Path

from a_normal.backtest.models import BacktestResult


def save_backtest_reports(result: BacktestResult, output_dir: str | Path) -> dict[str, Path]:
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    nav_path = base_dir / "daily_nav.csv"
    trades_path = base_dir / "trades.csv"
    metrics_path = base_dir / "metrics.csv"
    markdown_path = base_dir / "report.md"

    with nav_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["trade_date", "cash", "market_value", "total_equity", "nav", "positions"])
        writer.writeheader()
        for row in result.daily_nav:
            writer.writerow(row.model_dump(mode="json"))

    with trades_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "trade_date",
                "ts_code",
                "side",
                "price",
                "shares",
                "gross_amount",
                "commission",
                "stamp_tax",
                "total_cost",
                "cash_after",
                "reason",
            ],
        )
        writer.writeheader()
        for trade in result.trades:
            writer.writerow(trade.model_dump(mode="json"))

    with metrics_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "value"])
        for name, value in result.metrics.items():
            writer.writerow([name, value])

    lines = [
        "# 回测报告",
        "",
        f"- 初始资金: {result.initial_cash:.2f}",
        f"- 期末权益: {result.final_equity:.2f}",
        f"- 总收益率: {result.metrics['total_return']:.4%}",
        f"- 年化收益率: {result.metrics['annualized_return']:.4%}",
        f"- 最大回撤: {result.metrics['max_drawdown']:.4%}",
        f"- 夏普比率: {result.metrics['sharpe']:.4f}",
        f"- 胜率: {result.metrics['win_rate']:.4%}",
        f"- 换手率: {result.metrics['turnover']:.4f}",
        f"- 交易次数: {int(result.metrics['trade_count'])}",
        f"- 平均持仓天数: {result.metrics['average_holding_days']:.2f}",
        "",
    ]
    markdown_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "daily_nav": nav_path,
        "trades": trades_path,
        "metrics": metrics_path,
        "report": markdown_path,
    }
