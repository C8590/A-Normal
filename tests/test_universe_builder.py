from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import AnnouncementEvent, LocalCsvAdapter
from ashare_alpha.universe import ExcludeReason, UniverseBuilder, save_universe_csv


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")
SAMPLE_DATE = date(2026, 3, 20)


def build_sample_records():
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    builder = UniverseBuilder(
        config=load_project_config(),
        stock_master=adapter.load_stock_master(),
        daily_bars=adapter.load_daily_bars(),
        financial_summary=adapter.load_financial_summary(),
        announcement_events=adapter.load_announcement_events(),
    )
    return builder.build_for_date(SAMPLE_DATE)


def by_code(records, ts_code: str):
    return next(record for record in records if record.ts_code == ts_code)


def test_normal_main_board_stock_is_allowed() -> None:
    record = by_code(build_sample_records(), "600001.SH")

    assert record.is_allowed is True
    assert record.exclude_reasons == []
    assert record.avg_amount_20d is not None
    assert record.avg_amount_20d >= load_project_config().universe.min_avg_amount_20d


def test_chinext_star_and_bse_are_excluded() -> None:
    records = build_sample_records()

    assert ExcludeReason.BOARD_EXCLUDED in by_code(records, "300001.SZ").exclude_reasons
    assert ExcludeReason.BOARD_EXCLUDED in by_code(records, "688001.SH").exclude_reasons
    assert ExcludeReason.BOARD_EXCLUDED in by_code(records, "920001.BJ").exclude_reasons


def test_st_star_st_delisting_and_suspension_are_excluded() -> None:
    records = build_sample_records()

    assert ExcludeReason.IS_ST in by_code(records, "600003.SH").exclude_reasons
    assert ExcludeReason.IS_STAR_ST in by_code(records, "600004.SH").exclude_reasons
    assert ExcludeReason.DELISTING_RISK in by_code(records, "600006.SH").exclude_reasons
    assert ExcludeReason.SUSPENDED in by_code(records, "600005.SH").exclude_reasons


def test_new_listing_low_liquidity_expensive_and_negative_event_are_excluded() -> None:
    records = build_sample_records()

    assert ExcludeReason.LISTING_DAYS_TOO_SHORT in by_code(records, "001001.SZ").exclude_reasons
    assert ExcludeReason.LOW_AVG_AMOUNT_20D in by_code(records, "603999.SH").exclude_reasons
    assert ExcludeReason.TOO_EXPENSIVE_FOR_CAPITAL in by_code(records, "603999.SH").exclude_reasons
    assert ExcludeReason.RECENT_NEGATIVE_EVENT in by_code(records, "603999.SH").exclude_reasons
    assert by_code(records, "603999.SH").latest_negative_event_title == "Earnings expected to decline"


def test_missing_trade_date_bar_is_excluded() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    bars = [bar for bar in adapter.load_daily_bars() if not (bar.ts_code == "600001.SH" and bar.trade_date == SAMPLE_DATE)]
    builder = UniverseBuilder(
        config=load_project_config(),
        stock_master=adapter.load_stock_master(),
        daily_bars=bars,
        announcement_events=adapter.load_announcement_events(),
    )

    record = by_code(builder.build_for_date(SAMPLE_DATE), "600001.SH")

    assert ExcludeReason.MISSING_LATEST_BAR in record.exclude_reasons


def test_insufficient_daily_bars_are_excluded() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"]
    bars = [bar for bar in adapter.load_daily_bars() if bar.ts_code == "600001.SH" and bar.trade_date <= SAMPLE_DATE][:10]
    builder = UniverseBuilder(config=load_project_config(), stock_master=stock, daily_bars=bars)

    record = builder.build_for_date(bars[-1].trade_date)[0]

    assert ExcludeReason.INSUFFICIENT_DAILY_BARS in record.exclude_reasons


def test_future_data_is_not_used() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    future_event = AnnouncementEvent(
        event_time=datetime.combine(SAMPLE_DATE + timedelta(days=1), datetime.min.time()),
        ts_code="600001.SH",
        title="Future investigation should not be visible",
        source="sample_notice",
        event_type="investigation",
        event_direction="negative",
        event_strength=1.0,
        event_risk_level="high",
        raw_text=None,
    )
    builder = UniverseBuilder(
        config=load_project_config(),
        stock_master=[stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"],
        daily_bars=adapter.load_daily_bars(),
        announcement_events=[future_event],
    )

    record = builder.build_for_date(SAMPLE_DATE)[0]

    assert record.is_allowed is True
    assert record.has_recent_negative_event is False


def test_excluded_records_have_chinese_reason_and_stable_order() -> None:
    records = build_sample_records()

    assert [record.ts_code for record in records] == sorted(record.ts_code for record in records)
    excluded = [record for record in records if not record.is_allowed]
    assert excluded
    assert all(record.exclude_reason_text for record in excluded)
    assert all("；" in record.exclude_reason_text or len(record.exclude_reasons) == 1 for record in excluded)


def test_save_universe_csv_writes_output(tmp_path: Path) -> None:
    output_path = tmp_path / "universe.csv"

    save_universe_csv(build_sample_records(), output_path)

    assert output_path.exists()
    assert "exclude_reason_text" in output_path.read_text(encoding="utf-8")
