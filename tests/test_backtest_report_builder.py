from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.backtest import BacktestEngine, BacktestMetrics, BacktestResult, DailyEquityRecord, SimulatedTrade
from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.reports import BacktestReportBuilder, render_backtest_report_markdown


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")


def test_sample_backtest_no_trade_sets_reason() -> None:
    config = load_project_config()
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    result = BacktestEngine(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    ).run(date(2026, 1, 5), date(2026, 3, 20))

    report = BacktestReportBuilder(result, config, Path("outputs/reports/backtest")).build()

    assert report.no_trade is True
    assert report.no_trade_reason is not None
    assert "无模拟成交" in report.no_trade_reason


def test_rejected_trades_count_reject_reasons() -> None:
    report = BacktestReportBuilder(_result_with_rejection(), load_project_config(), Path("out")).build()

    assert report.top_reject_reasons == {"现金不足": 1}
    assert report.no_trade is True
    assert "现金不足" in report.no_trade_reason


def test_filled_fixture_builds_symbol_summary() -> None:
    report = BacktestReportBuilder(_result_with_fill(), load_project_config(), Path("out")).build()
    summary = report.trade_summary_by_symbol[0]

    assert summary.ts_code == "600001.SH"
    assert summary.filled_trades == 2
    assert summary.buy_count == 1
    assert summary.sell_count == 1
    assert summary.realized_pnl == 120


def test_equity_curve_tail_limited_to_five() -> None:
    report = BacktestReportBuilder(_result_with_fill(equity_rows=8), load_project_config(), Path("out")).build()

    assert len(report.equity_curve_tail) == 5


def test_backtest_markdown_contains_sections_and_disclaimer() -> None:
    markdown = render_backtest_report_markdown(
        BacktestReportBuilder(_result_with_rejection(), load_project_config(), Path("out")).build()
    )

    assert "核心指标" in markdown
    assert "交易摘要" in markdown
    assert "风险提示" in markdown
    assert "不构成投资建议" in markdown
    assert "稳赢" not in markdown
    assert "稳赚" not in markdown
    assert "必涨" not in markdown


def _metrics(trade_count: int, filled: int, rejected: int) -> BacktestMetrics:
    return BacktestMetrics(
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 20),
        initial_cash=10000,
        final_equity=10120 if filled else 10000,
        total_return=0.012 if filled else 0,
        annualized_return=0.05 if filled else 0,
        max_drawdown=-0.01 if filled else 0,
        sharpe=1.2 if filled else 0,
        win_rate=1.0 if filled else None,
        turnover=0.2 if filled else 0,
        trade_count=trade_count,
        filled_trade_count=filled,
        rejected_trade_count=rejected,
        average_holding_days=3 if filled else None,
    )


def _result_with_rejection() -> BacktestResult:
    return BacktestResult(
        metrics=_metrics(trade_count=1, filled=0, rejected=1),
        trades=[
            SimulatedTrade(
                decision_date=date(2026, 3, 19),
                execution_date=date(2026, 3, 20),
                ts_code="600001.SH",
                side="BUY",
                requested_shares=100,
                filled_shares=0,
                price=None,
                gross_value=0,
                commission=0,
                stamp_tax=0,
                transfer_fee=0,
                total_fee=0,
                net_cash_change=0,
                status="REJECTED",
                reject_reason="现金不足",
                realized_pnl=None,
                holding_days=None,
                reason="模拟买入",
            )
        ],
        daily_equity=_equity(3),
    )


def _result_with_fill(equity_rows: int = 3) -> BacktestResult:
    return BacktestResult(
        metrics=_metrics(trade_count=2, filled=2, rejected=0),
        trades=[
            SimulatedTrade(
                decision_date=date(2026, 3, 19),
                execution_date=date(2026, 3, 20),
                ts_code="600001.SH",
                side="BUY",
                requested_shares=100,
                filled_shares=100,
                price=10,
                gross_value=1000,
                commission=0.1,
                stamp_tax=0,
                transfer_fee=0,
                total_fee=0.1,
                net_cash_change=-1000.1,
                status="FILLED",
                reject_reason=None,
                realized_pnl=None,
                holding_days=None,
                reason="模拟买入",
            ),
            SimulatedTrade(
                decision_date=date(2026, 3, 23),
                execution_date=date(2026, 3, 24),
                ts_code="600001.SH",
                side="SELL",
                requested_shares=100,
                filled_shares=100,
                price=11.2,
                gross_value=1120,
                commission=0.1,
                stamp_tax=0.56,
                transfer_fee=0,
                total_fee=0.66,
                net_cash_change=1119.34,
                status="FILLED",
                reject_reason=None,
                realized_pnl=120,
                holding_days=4,
                reason="模拟卖出",
            ),
        ],
        daily_equity=_equity(equity_rows),
    )


def _equity(count: int) -> list[DailyEquityRecord]:
    return [
        DailyEquityRecord(
            trade_date=date(2026, 3, index + 1),
            cash=10000,
            market_value=0,
            total_equity=10000,
            positions_count=0,
            gross_exposure=0,
            daily_return=0,
            drawdown=0,
        )
        for index in range(count)
    ]
