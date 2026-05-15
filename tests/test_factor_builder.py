from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import DailyBar, LocalCsvAdapter, StockMaster
from ashare_alpha.factors import FactorBuilder, FactorMissingReason, save_factor_csv


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")
SAMPLE_DATE = date(2026, 3, 20)


def build_sample_records():
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    builder = FactorBuilder(
        config=load_project_config(),
        daily_bars=adapter.load_daily_bars(),
        stock_master=adapter.load_stock_master(),
    )
    return builder.build_for_date(SAMPLE_DATE)


def by_code(records, ts_code: str):
    return next(record for record in records if record.ts_code == ts_code)


def test_sample_data_generates_factor_daily() -> None:
    records = build_sample_records()

    assert len(records) == 12
    assert by_code(records, "600001.SH").is_computable is True
    assert by_code(records, "600001.SH").momentum_60d is not None


def test_factor_output_order_is_stable() -> None:
    records = build_sample_records()

    assert [record.ts_code for record in records] == sorted(record.ts_code for record in records)


def test_builder_does_not_use_future_data() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"]
    base_bars = adapter.load_daily_bars()
    future_bar = _bar("600001.SH", SAMPLE_DATE + timedelta(days=1), close=999.0)

    without_future = FactorBuilder(load_project_config(), base_bars, stock_master).build_for_date(SAMPLE_DATE)[0]
    with_future = FactorBuilder(load_project_config(), [*base_bars, future_bar], stock_master).build_for_date(SAMPLE_DATE)[0]

    assert with_future.latest_close == without_future.latest_close
    assert with_future.momentum_5d == without_future.momentum_5d


def test_missing_latest_bar_is_not_computable() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    bars = [bar for bar in adapter.load_daily_bars() if not (bar.ts_code == "600001.SH" and bar.trade_date == SAMPLE_DATE)]
    stock_master = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"]

    record = FactorBuilder(load_project_config(), bars, stock_master).build_for_date(SAMPLE_DATE)[0]

    assert record.is_computable is False
    assert FactorMissingReason.NO_LATEST_BAR_ON_DATE in record.missing_reasons


def test_not_trading_on_date_is_not_computable() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    suspended_bar = next(bar for bar in adapter.load_daily_bars() if bar.ts_code == "600005.SH" and not bar.is_trading)
    stock_master = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600005.SH"]

    record = FactorBuilder(load_project_config(), adapter.load_daily_bars(), stock_master).build_for_date(suspended_bar.trade_date)[0]

    assert record.is_computable is False
    assert FactorMissingReason.NOT_TRADING_ON_DATE in record.missing_reasons


def test_insufficient_history_has_missing_reason() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"]
    bars = [bar for bar in adapter.load_daily_bars() if bar.ts_code == "600001.SH"][:30]

    record = FactorBuilder(load_project_config(), bars, stock_master).build_for_date(bars[-1].trade_date)[0]

    assert record.is_computable is False
    assert FactorMissingReason.INSUFFICIENT_HISTORY in record.missing_reasons
    assert record.momentum_20d is not None
    assert record.momentum_60d is None


def test_one_bad_stock_does_not_block_other_records() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    missing_stock = StockMaster(
        ts_code="999999.SH",
        symbol="999999",
        name="No Bars",
        exchange="sse",
        board="main",
        industry=None,
        list_date="2010-01-01",
        delist_date=None,
        is_st=False,
        is_star_st=False,
        is_suspended=False,
        is_delisting_risk=False,
    )
    stock_master = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"] + [missing_stock]

    records = FactorBuilder(load_project_config(), adapter.load_daily_bars(), stock_master).build_for_date(SAMPLE_DATE)

    assert by_code(records, "600001.SH").is_computable is True
    assert by_code(records, "999999.SH").is_computable is False
    assert FactorMissingReason.NO_BARS in by_code(records, "999999.SH").missing_reasons


def test_missing_reasons_have_chinese_text() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"]
    bars = [bar for bar in adapter.load_daily_bars() if bar.ts_code == "600001.SH"][:10]

    record = FactorBuilder(load_project_config(), bars, stock_master).build_for_date(bars[-1].trade_date)[0]

    assert record.missing_reasons
    assert record.missing_reason_text


def test_save_factor_csv_writes_output(tmp_path: Path) -> None:
    output_path = tmp_path / "factor_daily.csv"

    save_factor_csv(build_sample_records(), output_path)

    assert output_path.exists()
    assert "momentum_20d" in output_path.read_text(encoding="utf-8")


def _bar(ts_code: str, trade_date: date, close: float) -> DailyBar:
    return DailyBar(
        trade_date=trade_date,
        ts_code=ts_code,
        open=close,
        high=close,
        low=close,
        close=close,
        pre_close=close,
        volume=1000,
        amount=close * 1000,
        turnover_rate=1.0,
        limit_up=close * 1.1,
        limit_down=close * 0.9,
        is_trading=True,
    )
