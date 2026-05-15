from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import AnnouncementEvent, LocalCsvAdapter
from ashare_alpha.events import EventFeatureBuilder, save_event_daily_csv


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")
SAMPLE_DATE = date(2026, 3, 20)


def build_sample_records():
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    builder = EventFeatureBuilder(
        config=load_project_config(),
        announcement_events=adapter.load_announcement_events(),
        stock_master=adapter.load_stock_master(),
    )
    return builder.build_for_date(SAMPLE_DATE)


def by_code(records, ts_code: str):
    return next(record for record in records if record.ts_code == ts_code)


def test_sample_data_generates_event_daily() -> None:
    records = build_sample_records()

    assert len(records) == 12
    assert by_code(records, "600001.SH").event_count == 1


def test_stock_without_events_still_has_record() -> None:
    record = by_code(build_sample_records(), "300001.SZ")

    assert record.event_count == 0
    assert record.event_reason == "近窗口内无有效公告事件"


def test_output_is_sorted_by_ts_code() -> None:
    records = build_sample_records()

    assert [record.ts_code for record in records] == sorted(record.ts_code for record in records)


def test_builder_does_not_use_future_events() -> None:
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = [stock for stock in adapter.load_stock_master() if stock.ts_code == "600001.SH"]
    future_event = _event(
        ts_code="600001.SH",
        event_time=datetime.combine(SAMPLE_DATE + timedelta(days=1), datetime.min.time()),
        event_type="investigation",
        title="未来立案调查",
        event_direction="negative",
        event_risk_level="high",
    )

    record = EventFeatureBuilder(
        load_project_config(),
        [future_event],
        stock_master,
    ).build_for_date(SAMPLE_DATE)[0]

    assert record.event_count == 0
    assert record.event_block_buy is False


def test_multiple_events_aggregate_score_and_risk() -> None:
    records = EventFeatureBuilder(
        load_project_config(),
        [
            _event(event_type="buyback", title="回购方案", event_strength=1.0),
            _event(
                event_time=datetime(2026, 3, 19, 10, 0),
                event_type="shareholder_reduce",
                title="股东减持计划",
                event_direction="negative",
                event_strength=1.0,
                event_risk_level="medium",
            ),
        ],
    ).build_for_date(SAMPLE_DATE)
    record = by_code(records, "600001.SH")

    assert record.event_count == 2
    assert record.event_score != 0
    assert record.event_risk_score > 0
    assert record.positive_event_count == 1
    assert record.negative_event_count == 1


def test_any_block_event_blocks_stock() -> None:
    record = EventFeatureBuilder(
        load_project_config(),
        [
            _event(
                event_type="investigation",
                title="公司收到立案调查通知",
                event_direction="negative",
                event_risk_level="high",
            )
        ],
    ).build_for_date(SAMPLE_DATE)[0]

    assert record.event_block_buy is True
    assert record.block_buy_reasons
    assert record.high_risk_event_count == 1


def test_latest_titles_use_most_recent_valid_events() -> None:
    records = EventFeatureBuilder(
        load_project_config(),
        [
            _event(event_time=datetime(2026, 3, 18, 9, 0), title="较早回购公告"),
            _event(
                event_time=datetime(2026, 3, 19, 9, 0),
                event_type="shareholder_reduce",
                event_direction="negative",
                title="最近减持公告",
                event_risk_level="medium",
            ),
        ],
    ).build_for_date(SAMPLE_DATE)
    record = by_code(records, "600001.SH")

    assert record.latest_event_title == "最近减持公告"
    assert record.latest_negative_event_title == "最近减持公告"


def test_event_reason_is_chinese_readable() -> None:
    record = by_code(build_sample_records(), "600006.SH")

    assert "触发禁买" in record.event_reason


def test_save_event_daily_csv_writes_output(tmp_path: Path) -> None:
    output_path = tmp_path / "event_daily.csv"

    save_event_daily_csv(build_sample_records(), output_path)

    assert output_path.exists()
    assert "event_reason" in output_path.read_text(encoding="utf-8")


def _event(
    ts_code: str = "600001.SH",
    event_time: datetime | None = None,
    event_type: str = "buyback",
    title: str = "回购方案公告",
    event_direction: str = "positive",
    event_strength: float = 1.0,
    event_risk_level: str = "low",
) -> AnnouncementEvent:
    return AnnouncementEvent(
        event_time=event_time or datetime(2026, 3, 20, 9, 0),
        ts_code=ts_code,
        title=title,
        source="exchange",
        event_type=event_type,
        event_direction=event_direction,
        event_strength=event_strength,
        event_risk_level=event_risk_level,
        raw_text=None,
    )
