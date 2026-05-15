from __future__ import annotations

from datetime import date, timedelta

from a_normal.cli import main
from a_normal.config import UniverseConfig
from a_normal.data import AnnouncementEvent, DailyBar, DataAdapter, FinancialSummary, StockMaster
from a_normal.universe import build_universe_daily, load_universe_config


class MemoryAdapter(DataAdapter):
    def __init__(
        self,
        stock_master: list[StockMaster],
        daily_bars: list[DailyBar],
        financial_summaries: list[FinancialSummary],
        announcement_events: list[AnnouncementEvent],
    ) -> None:
        self._stock_master = stock_master
        self._daily_bars = daily_bars
        self._financial_summaries = financial_summaries
        self._announcement_events = announcement_events

    def load_stock_master(self) -> list[StockMaster]:
        return self._stock_master

    def load_daily_bars(self) -> list[DailyBar]:
        return self._daily_bars

    def load_financial_summaries(self) -> list[FinancialSummary]:
        return self._financial_summaries

    def load_announcement_events(self) -> list[AnnouncementEvent]:
        return self._announcement_events


def test_build_universe_daily_covers_each_exclude_reason():
    target_date = date(2026, 1, 6)
    stocks = [
        stock("000001.SZ", "Allowed Co"),
        stock("000002.SZ", "ST Bad Co", is_st=True),
        stock("000003.SZ", "Delisting Risk Co"),
        stock("000004.SZ", "Suspended Co"),
        stock("000005.SZ", "New Listing Co"),
        stock("300001.SZ", "ChiNext Co"),
        stock("000006.SZ", "Illiquid Co"),
        stock("000007.SZ", "Expensive Co"),
        stock("000008.SZ", "Negative Event Co"),
    ]
    bars = []
    bars.extend(make_bars("000001.SZ", close=5, amount=5000, target_date=target_date))
    bars.extend(make_bars("000002.SZ", close=5, amount=5000, target_date=target_date))
    bars.extend(make_bars("000003.SZ", close=5, amount=5000, target_date=target_date))
    bars.extend(make_bars("000004.SZ", close=5, amount=5000, target_date=target_date, suspended_on_target=True))
    bars.extend(make_bars("000005.SZ", close=5, amount=5000, target_date=target_date, days=1))
    bars.extend(make_bars("300001.SZ", close=5, amount=5000, target_date=target_date))
    bars.extend(make_bars("000006.SZ", close=5, amount=10, target_date=target_date))
    bars.extend(make_bars("000007.SZ", close=20, amount=5000, target_date=target_date))
    bars.extend(make_bars("000008.SZ", close=5, amount=5000, target_date=target_date))
    events = [
        AnnouncementEvent(
            stock_code="000008.SZ",
            event_date=target_date,
            category="penalty",
            title="regulatory penalty notice",
        )
    ]
    adapter = MemoryAdapter(stocks, bars, make_financials(stocks), events)
    config = UniverseConfig(
        min_listing_trading_days=3,
        liquidity_lookback_days=3,
        min_avg_amount_20d=1000,
        initial_capital=1000,
        lot_size=100,
        max_position_pct_for_entry=1,
        negative_event_categories=("penalty",),
        negative_event_keywords=("regulatory penalty",),
        delisting_risk_keywords=("delisting risk",),
    )

    result = build_universe_daily(target_date, adapter=adapter, config=config)
    rows = {row.ts_code: row for row in result.rows}

    assert rows["000001.SZ"].is_allowed is True
    assert rows["000001.SZ"].exclude_reasons == ()
    assert rows["000002.SZ"].exclude_reasons == ("st_stock",)
    assert rows["000003.SZ"].exclude_reasons == ("delisting_risk",)
    assert rows["000004.SZ"].exclude_reasons == ("suspended",)
    assert rows["000005.SZ"].exclude_reasons == ("listing_days_lt_threshold",)
    assert rows["300001.SZ"].exclude_reasons == ("not_mainboard",)
    assert rows["000006.SZ"].exclude_reasons == ("low_liquidity",)
    assert rows["000007.SZ"].exclude_reasons == ("price_too_high_for_capital",)
    assert rows["000008.SZ"].exclude_reasons == ("recent_negative_event",)
    assert all(row.exclude_reasons for row in rows.values() if not row.is_allowed)


def test_universe_config_loads_from_yaml():
    config = load_universe_config()

    assert config.min_listing_trading_days == 120
    assert config.liquidity_lookback_days == 20
    assert config.min_avg_amount_20d == 10000000


def test_cli_build_universe_runs_against_sample_data(capsys):
    exit_code = main(["build-universe", "--date", "2026-03-26"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.splitlines()[0] == "ts_code,is_allowed,exclude_reasons,liquidity_score,risk_score"
    assert "000001.SZ" in captured.out


def stock(code: str, name: str, is_st: bool = False) -> StockMaster:
    exchange = "SSE" if code.endswith(".SH") else "SZSE"
    return StockMaster(
        stock_code=code,
        stock_name=name,
        exchange=exchange,
        listed_date="2020-01-01",
        industry="Test",
        is_st=is_st,
    )


def make_bars(
    code: str,
    close: float,
    amount: float,
    target_date: date,
    days: int = 5,
    suspended_on_target: bool = False,
) -> list[DailyBar]:
    start = target_date - timedelta(days=days - 1)
    bars = []
    for offset in range(days):
        trade_date = start + timedelta(days=offset)
        bars.append(
            DailyBar(
                stock_code=code,
                trade_date=trade_date,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=0 if suspended_on_target and trade_date == target_date else 1000,
                amount=amount,
                is_suspended=suspended_on_target and trade_date == target_date,
            )
        )
    return bars


def make_financials(stocks: list[StockMaster]) -> list[FinancialSummary]:
    return [
        FinancialSummary(
            stock_code=item.stock_code,
            report_date="2025-12-31",
            revenue=1000,
            net_profit=100,
            total_assets=2000,
            total_equity=1000,
        )
        for item in stocks
    ]
