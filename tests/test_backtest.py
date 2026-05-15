from __future__ import annotations

from datetime import date, timedelta

from a_normal.backtest import BacktestEngine, run_backtest, save_backtest_reports
from a_normal.config import FeesConfig, TradingRulesConfig
from a_normal.data import DailyBar, LocalCsvAdapter
from a_normal.signals import SignalDaily


def test_backtest_executes_lot_trades_tracks_cash_positions_logs_and_nav():
    bars = make_bars("000001.SZ", [10, 10.2, 10.4], start=date(2026, 1, 1))
    signals = [
        signal("000001.SZ", "2026-01-01", "BUY", target_weight=0.5),
        signal("000001.SZ", "2026-01-02", "SELL", target_weight=0),
    ]

    result = engine().run(bars, signals)

    assert len(result.trades) == 2
    assert result.trades[0].side == "BUY"
    assert result.trades[0].shares % 100 == 0
    assert result.trades[1].side == "SELL"
    assert result.daily_nav[0].positions["000001.SZ"] == result.trades[0].shares
    assert result.daily_nav[-1].positions == {}
    assert result.metrics["trade_count"] == 2
    assert "total_return" in result.metrics
    assert "average_holding_days" in result.metrics


def test_backtest_blocks_suspended_and_limit_up_buy():
    suspended = DailyBar(
        stock_code="000001.SZ",
        trade_date="2026-01-01",
        open=10,
        high=10,
        low=10,
        close=10,
        volume=0,
        amount=0,
        is_suspended=True,
    )
    limit_bars = make_bars("000002.SZ", [10, 11], start=date(2026, 1, 1))
    signals = [
        signal("000001.SZ", "2026-01-01", "BUY", target_weight=0.5),
        signal("000002.SZ", "2026-01-02", "BUY", target_weight=0.5),
    ]

    result = engine().run([suspended, *limit_bars], signals)

    assert result.trades == ()
    assert all(nav.positions == {} for nav in result.daily_nav)


def test_backtest_blocks_limit_down_sell_and_respects_t_plus_one_lock():
    bars = make_bars("000001.SZ", [10, 10, 9], start=date(2026, 1, 1))
    signals = [
        signal("000001.SZ", "2026-01-01", "BUY", target_weight=0.5),
        signal("000001.SZ", "2026-01-01", "SELL", target_weight=0),
        signal("000001.SZ", "2026-01-03", "SELL", target_weight=0),
    ]

    result = engine().run(bars, signals)

    assert len(result.trades) == 1
    assert result.trades[0].side == "BUY"
    assert result.daily_nav[-1].positions["000001.SZ"] > 0


def test_backtest_reports_are_written(tmp_path):
    result = engine().run(
        make_bars("000001.SZ", [10, 10.2], start=date(2026, 1, 1)),
        [signal("000001.SZ", "2026-01-01", "BUY", target_weight=0.5)],
    )

    paths = save_backtest_reports(result, tmp_path)

    assert paths["daily_nav"].exists()
    assert paths["trades"].exists()
    assert paths["metrics"].exists()
    assert paths["report"].exists()
    assert "total_return" in paths["metrics"].read_text(encoding="utf-8")


def test_sample_data_can_run_complete_backtest(tmp_path):
    adapter = LocalCsvAdapter()
    signals = [
        signal("000001.SZ", "2026-01-02", "BUY", target_weight=0.2),
        signal("000001.SZ", "2026-01-05", "SELL", target_weight=0),
    ]

    result = run_backtest(adapter.load_daily_bars(), signals, initial_cash=10_000)
    paths = save_backtest_reports(result, tmp_path)

    assert result.daily_nav
    assert set(result.metrics) == {
        "total_return",
        "annualized_return",
        "max_drawdown",
        "sharpe",
        "win_rate",
        "turnover",
        "trade_count",
        "average_holding_days",
    }
    assert paths["report"].exists()


def engine() -> BacktestEngine:
    return BacktestEngine(
        initial_cash=10_000,
        trading_rules=TradingRulesConfig(lot_size=100, price_tick=0.01, t_plus_one=True, normal_limit_pct=0.10),
        fees=FeesConfig(commission_rate=0.00005, min_commission=0.1, stamp_tax_rate_on_sell=0.0005, slippage_bps=0),
    )


def signal(ts_code: str, trade_date: str, signal_name: str, target_weight: float) -> SignalDaily:
    return SignalDaily(
        ts_code=ts_code,
        trade_date=trade_date,
        stock_score=80 if signal_name == "BUY" else 20,
        risk_level="low",
        signal=signal_name,
        target_weight=target_weight,
        reason="测试信号",
    )


def make_bars(ts_code: str, closes: list[float], start: date) -> list[DailyBar]:
    bars = []
    for index, close in enumerate(closes):
        bars.append(
            DailyBar(
                stock_code=ts_code,
                trade_date=start + timedelta(days=index),
                open=close,
                high=close,
                low=close,
                close=close,
                volume=100000,
                amount=close * 100000,
            )
        )
    return bars
