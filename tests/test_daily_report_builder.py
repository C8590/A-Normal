from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.events import EventFeatureBuilder
from ashare_alpha.factors import FactorBuilder
from ashare_alpha.reports import DailyReportBuilder, render_daily_report_markdown
from ashare_alpha.signals import SignalGenerator
from ashare_alpha.universe import UniverseBuilder


SAMPLE_DATA_DIR = Path("data/sample/ashare_alpha")
SAMPLE_CONFIG_DIR = Path("configs/ashare_alpha")
SAMPLE_DATE = date(2026, 3, 20)


def test_sample_data_can_generate_daily_research_report() -> None:
    report = _sample_report()

    assert report.report_date == SAMPLE_DATE
    assert report.total_stocks == 12
    assert report.market_regime


def test_buy_zero_markdown_says_no_buy_signal() -> None:
    markdown = render_daily_report_markdown(_sample_report())

    assert "当前无 BUY 信号" in markdown


def test_universe_exclude_reason_enters_blocked_stocks() -> None:
    report = _sample_report()

    assert any(item.universe_exclude_reason_text for item in report.blocked_stocks)


def test_event_block_buy_enters_event_risk_list() -> None:
    report = _sample_report()

    assert any(item.ts_code == "600006.SH" for item in report.recent_event_risk_stocks)


def test_buy_candidates_sorted_by_stock_score_desc() -> None:
    report = _sample_report()
    scores = [item.stock_score for item in report.buy_candidates]

    assert scores == sorted(scores, reverse=True)


def test_watch_candidates_limited_to_20() -> None:
    report = _sample_report()

    assert len(report.watch_candidates) <= 20


def test_config_summary_fields_present() -> None:
    report = _sample_report()

    assert report.initial_cash == 10000
    assert report.max_positions == 2
    assert report.commission_rate == 0.00005
    assert report.stamp_tax_rate_on_sell == 0.0005


def test_daily_report_contains_disclaimer_without_return_promise() -> None:
    text = render_daily_report_markdown(_sample_report())

    assert "不构成投资建议" in text
    assert "自动下单" in text
    assert "稳赢" not in text
    assert "稳赚" not in text
    assert "必涨" not in text


def _sample_report():
    config = load_project_config(SAMPLE_CONFIG_DIR)
    adapter = LocalCsvAdapter(SAMPLE_DATA_DIR)
    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    events = adapter.load_announcement_events()
    universe_records = UniverseBuilder(config, stock_master, daily_bars, financial_summary, events).build_for_date(SAMPLE_DATE)
    factor_records = FactorBuilder(config, daily_bars, stock_master).build_for_date(SAMPLE_DATE)
    event_records = EventFeatureBuilder(config, events, stock_master).build_for_date(SAMPLE_DATE)
    signal_records = SignalGenerator(
        config,
        stock_master,
        financial_summary,
        universe_records,
        factor_records,
        event_records,
    ).generate_for_date(SAMPLE_DATE)
    return DailyReportBuilder(
        config=config,
        stock_master=stock_master,
        universe_records=universe_records,
        factor_records=factor_records,
        event_records=event_records,
        signal_records=signal_records,
        data_dir=SAMPLE_DATA_DIR,
        config_dir=SAMPLE_CONFIG_DIR,
    ).build(SAMPLE_DATE)
