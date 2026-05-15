from __future__ import annotations

from datetime import date, datetime

from ashare_alpha.reports import BacktestResearchReport, DailyResearchReport, ReportStockItem, report_to_json_dict


def test_report_stock_item_validates() -> None:
    item = _stock_item()

    assert item.ts_code == "600001.SH"
    assert item.reason


def test_daily_research_report_validates() -> None:
    report = DailyResearchReport(
        report_date=date(2026, 3, 20),
        generated_at=datetime(2026, 3, 20, 18, 0),
        data_dir="data/sample/ashare_alpha",
        config_dir="configs/ashare_alpha",
        total_stocks=1,
        allowed_universe_count=1,
        blocked_universe_count=0,
        buy_count=1,
        watch_count=0,
        block_count=0,
        high_risk_count=0,
        market_regime="normal",
        market_regime_score=60,
        buy_candidates=[_stock_item()],
        watch_candidates=[],
        blocked_stocks=[],
        high_risk_stocks=[],
        recent_event_risk_stocks=[],
        universe_exclude_reason_counts={},
        signal_reason_counts={"BUY": 1},
        event_block_buy_count=0,
        event_high_risk_count=0,
        average_stock_score=80,
        average_risk_score=5,
        initial_cash=10000,
        max_positions=2,
        max_position_weight=0.6,
        lot_size=100,
        commission_rate=0.00005,
        min_commission=0.1,
        stamp_tax_rate_on_sell=0.0005,
        slippage_bps=5,
    )

    assert report.buy_count == 1


def test_backtest_research_report_validates_and_serializes_dates() -> None:
    report = BacktestResearchReport(
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 20),
        generated_at=datetime(2026, 3, 20, 18, 0),
        output_dir="outputs/reports/backtest",
        initial_cash=10000,
        final_equity=10000,
        total_return=0,
        annualized_return=0,
        max_drawdown=0,
        sharpe=0,
        win_rate=None,
        turnover=0,
        trade_count=0,
        filled_trade_count=0,
        rejected_trade_count=0,
        average_holding_days=None,
        no_trade=True,
        no_trade_reason="样例数据和当前评分阈值下没有 BUY 信号，因此无模拟成交。",
        top_reject_reasons={},
        trade_summary_by_symbol=[],
        equity_curve_tail=[],
        initial_cash_config=10000,
        max_positions=2,
        max_position_weight=0.6,
        rebalance_frequency="weekly",
        execution_price="next_open",
        t_plus_one=True,
        lot_size=100,
        commission_rate=0.00005,
        min_commission=0.1,
        stamp_tax_rate_on_sell=0.0005,
        slippage_bps=5,
    )
    payload = report_to_json_dict(report)

    assert payload["start_date"] == "2026-01-05"
    assert payload["generated_at"] == "2026-03-20T18:00:00"


def _stock_item() -> ReportStockItem:
    return ReportStockItem(
        ts_code="600001.SH",
        name="测试股票",
        industry="工业",
        signal="BUY",
        stock_score=80,
        risk_level="low",
        target_weight=0.2,
        target_shares=100,
        estimated_position_value=1000,
        latest_close=10,
        liquidity_score=80,
        event_score=0,
        event_risk_score=0,
        reason="BUY：综合评分较高，风险等级 low。",
        buy_reasons=["综合评分 80.0"],
        risk_reasons=[],
        universe_exclude_reason_text=None,
        event_reason=None,
    )
