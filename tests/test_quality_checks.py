from __future__ import annotations

from datetime import date

from ashare_alpha.quality.checks import (
    check_announcement_event,
    check_cross_table_coverage,
    check_daily_bar,
    check_financial_summary,
    check_stock_master,
)


def test_stock_master_duplicate_ts_code_error() -> None:
    issues = check_stock_master([_stock("600001.SH"), _stock("600001.SH")])

    assert _has(issues, "duplicate_ts_code", "error")


def test_stock_master_board_prefix_conflict_warning() -> None:
    issues = check_stock_master([_stock("300001.SZ", board="main", exchange="szse")])

    assert _has(issues, "board_prefix_conflict", "warning")


def test_daily_bar_high_below_low_error() -> None:
    issues = check_daily_bar([_bar(high="9", low="10")], {"600001.SH"})

    assert _has(issues, "high_below_low", "error")


def test_daily_bar_unknown_ts_code_error() -> None:
    issues = check_daily_bar([_bar(ts_code="999999.SH")], {"600001.SH"})

    assert _has(issues, "unknown_ts_code", "error")


def test_daily_bar_trading_amount_zero_warning() -> None:
    issues = check_daily_bar([_bar(amount="0", volume="0", is_trading="true")], {"600001.SH"})

    assert _has(issues, "trading_with_nonpositive_amount", "warning")


def test_daily_bar_close_above_limit_up_warning() -> None:
    issues = check_daily_bar([_bar(close="11.2", high="11.3", limit_up="11.0")], {"600001.SH"})

    assert _has(issues, "close_above_limit_up", "warning")


def test_financial_publish_before_report_error() -> None:
    issues = check_financial_summary([_financial(publish_date="2025-12-30")], {"600001.SH"})

    assert _has(issues, "publish_before_report", "error")


def test_financial_extreme_debt_to_asset_warning() -> None:
    issues = check_financial_summary([_financial(debt_to_asset="2")], {"600001.SH"})

    assert _has(issues, "extreme_debt_to_asset", "warning")


def test_announcement_event_strength_invalid_error() -> None:
    issues = check_announcement_event([_event(event_strength="2")], {"600001.SH"}, date(2026, 3, 20))

    assert _has(issues, "invalid_event_strength", "error")


def test_announcement_event_duplicate_warning() -> None:
    event = _event()
    issues = check_announcement_event([event, event], {"600001.SH"}, date(2026, 3, 20))

    assert _has(issues, "duplicate_announcement_event", "warning")


def test_stock_without_daily_bar_warning() -> None:
    issues = check_cross_table_coverage([_stock("600001.SH")], [], [], [], None)

    assert _has(issues, "stock_without_daily_bar", "warning")


def test_daily_bar_range_too_short_warning() -> None:
    issues = check_cross_table_coverage([_stock("600001.SH")], [_bar(trade_date="2026-03-20")], [], [], None)

    assert _has(issues, "daily_bar_range_too_short", "warning")


def _stock(ts_code: str, board: str = "main", exchange: str = "sse") -> dict[str, str]:
    return {
        "ts_code": ts_code,
        "symbol": ts_code[:6],
        "name": "Sample",
        "exchange": exchange,
        "board": board,
        "list_date": "2010-01-04",
        "delist_date": "",
    }


def _bar(**overrides) -> dict[str, str]:
    payload = {
        "trade_date": "2026-03-20",
        "ts_code": "600001.SH",
        "open": "10",
        "high": "10.5",
        "low": "9.8",
        "close": "10",
        "pre_close": "10",
        "volume": "100",
        "amount": "1000",
        "limit_up": "11",
        "limit_down": "9",
        "is_trading": "true",
    }
    payload.update(overrides)
    return payload


def _financial(**overrides) -> dict[str, str]:
    payload = {
        "report_date": "2025-12-31",
        "publish_date": "2026-03-20",
        "ts_code": "600001.SH",
        "debt_to_asset": "0.5",
        "goodwill_to_equity": "0.1",
        "gross_margin": "0.3",
        "roe": "0.1",
        "operating_cashflow_to_profit": "1",
    }
    payload.update(overrides)
    return payload


def _event(**overrides) -> dict[str, str]:
    payload = {
        "event_time": "2026-03-20T09:30:00",
        "ts_code": "600001.SH",
        "title": "公告",
        "source": "sample",
        "event_strength": "0.5",
        "event_direction": "positive",
        "event_risk_level": "low",
    }
    payload.update(overrides)
    return payload


def _has(issues, issue_type: str, severity: str) -> bool:
    return any(issue.issue_type == issue_type and issue.severity == severity for issue in issues)

