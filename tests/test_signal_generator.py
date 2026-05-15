from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import FinancialSummary, LocalCsvAdapter, StockMaster
from ashare_alpha.events import EventDailyRecord, EventFeatureBuilder
from ashare_alpha.factors import FactorBuilder
from ashare_alpha.signals import SignalGenerator, save_signal_csv
from ashare_alpha.universe import UniverseBuilder
from tests_support import factor, universe


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")
SAMPLE_DATE = date(2026, 3, 20)


def test_sample_data_generates_signal_daily() -> None:
    records = _sample_records()

    assert len(records) == 12
    assert all(record.reason for record in records)


def test_universe_blocked_stock_gets_block_signal() -> None:
    record = _by_code(_sample_records(), "300001.SZ")

    assert record.signal == "BLOCK"
    assert record.universe_allowed is False


def test_event_block_buy_stock_gets_block_signal() -> None:
    record = _by_code(_sample_records(), "600006.SH")

    assert record.event_block_buy is True
    assert record.signal == "BLOCK"


def test_high_risk_level_blocks_signal() -> None:
    record = _by_code(_sample_records(), "600006.SH")

    assert record.risk_level == "high"
    assert record.signal == "BLOCK"


def test_qualified_high_score_stock_gets_buy() -> None:
    records = _custom_records(event_score=40, liquidity_score=100)
    buy_records = [record for record in records if record.signal == "BUY"]

    assert buy_records
    assert all(record.stock_score >= load_project_config().scoring.thresholds.buy for record in buy_records)


def test_watch_score_range_gets_watch() -> None:
    record = _custom_records(event_score=0, liquidity_score=80)[0]

    assert load_project_config().scoring.thresholds.watch <= record.stock_score < load_project_config().scoring.thresholds.buy
    assert record.signal == "WATCH"


def test_risk_market_generates_no_buy() -> None:
    records = _custom_records(
        event_score=40,
        liquidity_score=100,
        factor_overrides={
            "momentum_5d": -0.02,
            "momentum_20d": -0.03,
            "momentum_60d": -0.04,
            "close_above_ma20": False,
            "close_above_ma60": False,
        },
    )

    assert {record.market_regime for record in records} == {"risk"}
    assert all(record.signal != "BUY" for record in records)


def test_buy_count_does_not_exceed_max_positions() -> None:
    records = _custom_records(event_score=40, liquidity_score=100)

    assert sum(1 for record in records if record.signal == "BUY") <= load_project_config().backtest.max_positions


def test_buy_target_shares_are_lot_multiples() -> None:
    records = _custom_records(event_score=40, liquidity_score=100)
    lot_size = load_project_config().trading_rules.lot_size

    assert all(record.target_shares % lot_size == 0 for record in records if record.signal == "BUY")


def test_low_estimated_position_value_downgrades_to_watch() -> None:
    config = load_project_config()
    config = config.model_copy(
        update={"backtest": config.backtest.model_copy(update={"min_position_value": 5000})},
    )
    record = _custom_records(config=config, event_score=40, liquidity_score=100)[0]

    assert record.signal == "WATCH"
    assert "目标金额低于最小持仓金额" in record.reason


def test_every_record_has_chinese_reason_and_stable_order() -> None:
    records = _sample_records()

    assert [record.ts_code for record in records] == sorted(record.ts_code for record in records)
    assert all(record.reason for record in records)


def test_save_signal_csv_writes_output(tmp_path: Path) -> None:
    output_path = tmp_path / "signal_daily.csv"

    save_signal_csv(_sample_records(), output_path)

    assert output_path.exists()
    assert "stock_score" in output_path.read_text(encoding="utf-8")


def _sample_records():
    config = load_project_config()
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    events = adapter.load_announcement_events()
    universe_records = UniverseBuilder(config, stock_master, daily_bars, financial_summary, events).build_for_date(SAMPLE_DATE)
    factor_records = FactorBuilder(config, daily_bars, stock_master).build_for_date(SAMPLE_DATE)
    event_records = EventFeatureBuilder(config, events, stock_master).build_for_date(SAMPLE_DATE)
    return SignalGenerator(
        config,
        stock_master,
        financial_summary,
        universe_records,
        factor_records,
        event_records,
    ).generate_for_date(SAMPLE_DATE)


def _custom_records(
    config=None,
    event_score: float = 0,
    liquidity_score: float = 80,
    factor_overrides: dict | None = None,
):
    config = config or load_project_config()
    stocks = [_stock("600001.SH"), _stock("600002.SH"), _stock("600003.SH")]
    factors = [factor(stock.ts_code, **(factor_overrides or {})) for stock in stocks]
    universes = [universe(stock.ts_code, liquidity_score=liquidity_score, risk_score=0) for stock in stocks]
    events = [_event(stock.ts_code, event_score=event_score) for stock in stocks]
    financials = [_financial(stock.ts_code) for stock in stocks]
    return SignalGenerator(config, stocks, financials, universes, factors, events).generate_for_date(SAMPLE_DATE)


def _by_code(records, ts_code: str):
    return next(record for record in records if record.ts_code == ts_code)


def _stock(ts_code: str) -> StockMaster:
    return StockMaster(
        ts_code=ts_code,
        symbol=ts_code[:6],
        name=ts_code,
        exchange="sse",
        board="main",
        industry="industrial",
        list_date="2010-01-01",
        delist_date=None,
        is_st=False,
        is_star_st=False,
        is_suspended=False,
        is_delisting_risk=False,
    )


def _event(ts_code: str, event_score: float) -> EventDailyRecord:
    return EventDailyRecord(
        trade_date=SAMPLE_DATE,
        ts_code=ts_code,
        event_score=event_score,
        event_risk_score=0,
        event_count=1,
        positive_event_count=1 if event_score > 0 else 0,
        negative_event_count=1 if event_score < 0 else 0,
        high_risk_event_count=0,
        event_block_buy=False,
        block_buy_reasons=[],
        latest_event_title="回购公告",
        latest_negative_event_title=None,
        event_reason="正向事件",
    )


def _financial(ts_code: str) -> FinancialSummary:
    return FinancialSummary(
        report_date=date(2025, 12, 31),
        publish_date=SAMPLE_DATE,
        ts_code=ts_code,
        revenue_yoy=10,
        profit_yoy=10,
        net_profit_yoy=10,
        roe=12,
        gross_margin=30,
        debt_to_asset=30,
        operating_cashflow_to_profit=1.0,
        goodwill_to_equity=5,
    )
