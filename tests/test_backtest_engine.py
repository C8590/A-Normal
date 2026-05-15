from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ashare_alpha.backtest import BacktestEngine, Portfolio
from ashare_alpha.config import load_project_config
from ashare_alpha.data import AnnouncementEvent, LocalCsvAdapter
from ashare_alpha.signals import SignalGenerator


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")


def test_sample_data_runs_complete_backtest_with_zero_buy() -> None:
    result = _engine(load_project_config()).run(date(2026, 1, 5), date(2026, 3, 20))

    assert result.daily_equity
    assert result.metrics.trade_count == 0
    assert result.metrics.final_equity == 10000


def test_zero_buy_backtest_does_not_error() -> None:
    result = _engine(load_project_config()).run(date(2026, 3, 16), date(2026, 3, 20))

    assert result.metrics.filled_trade_count == 0


def test_lowered_thresholds_can_produce_simulated_trade() -> None:
    result = _engine(_buy_config()).run(date(2026, 3, 16), date(2026, 3, 24))

    assert any(trade.status == "FILLED" and trade.side == "BUY" for trade in result.trades)


def test_signal_decision_date_executes_on_next_trading_date() -> None:
    result = _engine(_buy_config()).run(date(2026, 3, 16), date(2026, 3, 24))
    filled = next(trade for trade in result.trades if trade.status == "FILLED")

    assert filled.decision_date < filled.execution_date


def test_future_event_after_decision_date_does_not_block_current_signal() -> None:
    config = _buy_config()
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    future_event = AnnouncementEvent(
        event_time=datetime(2026, 3, 21, 9, 0),
        ts_code="600001.SH",
        title="未来立案调查",
        source="exchange",
        event_type="investigation",
        event_direction="negative",
        event_strength=1.0,
        event_risk_level="high",
        raw_text=None,
    )
    engine = BacktestEngine(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        [*adapter.load_announcement_events(), future_event],
    )

    result = engine.run(date(2026, 3, 16), date(2026, 3, 23))

    assert any(trade.status == "FILLED" and trade.side == "BUY" for trade in result.trades)


def test_order_generation_sells_before_buys() -> None:
    config = _buy_config()
    engine = _engine(config)
    portfolio = Portfolio(10_000, config.trading_rules)
    portfolio.buy("600003.SH", 100, 10, date(2026, 3, 18), -1000)
    signals = _signals_for(config, date(2026, 3, 20))

    orders = engine._build_orders(signals, date(2026, 3, 20), date(2026, 3, 23), 10_000, portfolio)

    assert orders
    assert orders[0].side == "SELL"


def test_buy_count_does_not_exceed_max_positions() -> None:
    result = _engine(_buy_config()).run(date(2026, 3, 16), date(2026, 3, 24))
    buy_count = sum(1 for trade in result.trades if trade.status == "FILLED" and trade.side == "BUY")

    assert buy_count <= load_project_config().backtest.max_positions


def test_filled_buy_shares_are_lot_multiples() -> None:
    config = _buy_config()
    result = _engine(config).run(date(2026, 3, 16), date(2026, 3, 24))

    assert all(trade.filled_shares % config.trading_rules.lot_size == 0 for trade in result.trades if trade.status == "FILLED")


def test_block_signal_attempts_exit_on_next_rebalance() -> None:
    config = _buy_config(rebalance_frequency="daily")
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    block_event = AnnouncementEvent(
        event_time=datetime(2026, 3, 23, 16, 0),
        ts_code="600001.SH",
        title="立案调查",
        source="exchange",
        event_type="investigation",
        event_direction="negative",
        event_strength=1.0,
        event_risk_level="high",
        raw_text=None,
    )
    result = BacktestEngine(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        [*adapter.load_announcement_events(), block_event],
    ).run(date(2026, 3, 20), date(2026, 3, 25))

    assert any(trade.side == "SELL" for trade in result.trades)


def test_limit_down_sell_is_rejected() -> None:
    config = _buy_config(rebalance_frequency="daily")
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    bars = []
    for bar in adapter.load_daily_bars():
        if bar.ts_code == "600001.SH" and bar.trade_date == date(2026, 3, 24):
            bars.append(bar.model_copy(update={"open": bar.limit_down, "close": bar.limit_down}))
        else:
            bars.append(bar)
    block_event = AnnouncementEvent(
        event_time=datetime(2026, 3, 23, 16, 0),
        ts_code="600001.SH",
        title="立案调查",
        source="exchange",
        event_type="investigation",
        event_direction="negative",
        event_strength=1.0,
        event_risk_level="high",
        raw_text=None,
    )

    result = BacktestEngine(
        config,
        adapter.load_stock_master(),
        bars,
        adapter.load_financial_summary(),
        [*adapter.load_announcement_events(), block_event],
    ).run(date(2026, 3, 20), date(2026, 3, 25))

    assert any(trade.side == "SELL" and trade.status == "REJECTED" and trade.reject_reason and "跌停" in trade.reject_reason for trade in result.trades)


def test_daily_equity_length_matches_trading_dates_and_final_equity_consistent() -> None:
    result = _engine(load_project_config()).run(date(2026, 3, 16), date(2026, 3, 20))

    assert len(result.daily_equity) == 5
    assert result.metrics.final_equity == result.daily_equity[-1].cash + result.daily_equity[-1].market_value


def _engine(config) -> BacktestEngine:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    return BacktestEngine(
        config,
        adapter.load_stock_master(),
        adapter.load_daily_bars(),
        adapter.load_financial_summary(),
        adapter.load_announcement_events(),
    )


def _buy_config(rebalance_frequency: str = "weekly"):
    config = load_project_config()
    scoring = config.scoring.model_copy(
        update={
            "thresholds": config.scoring.thresholds.model_copy(update={"buy": 60, "watch": 40}),
            "position_sizing": config.scoring.position_sizing.model_copy(
                update={"min_buy_score": 60, "strong_buy_score": 80}
            ),
        }
    )
    backtest = config.backtest.model_copy(update={"rebalance_frequency": rebalance_frequency})
    return config.model_copy(update={"scoring": scoring, "backtest": backtest})


def _signals_for(config, trade_date: date):
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    events = adapter.load_announcement_events()
    from ashare_alpha.events import EventFeatureBuilder
    from ashare_alpha.factors import FactorBuilder
    from ashare_alpha.universe import UniverseBuilder

    return SignalGenerator(
        config=config,
        stock_master=stock_master,
        financial_summary=financial_summary,
        universe_records=UniverseBuilder(config, stock_master, daily_bars, financial_summary, events).build_for_date(trade_date),
        factor_records=FactorBuilder(config, daily_bars, stock_master).build_for_date(trade_date),
        event_records=EventFeatureBuilder(config, events, stock_master).build_for_date(trade_date),
    ).generate_for_date(trade_date)
