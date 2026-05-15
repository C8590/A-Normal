from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from typing import Any

from ashare_alpha.quality.models import QualityIssue


def check_trade_calendar(rows: list[dict[str, str]]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    calendar_dates = [_parse_date(row.get("calendar_date")) for row in rows]
    for calendar_date, count in Counter(item for item in calendar_dates if item is not None).items():
        if count > 1:
            issues.append(_issue("error", "trade_calendar", "duplicate_calendar_date", None, "calendar_date", "calendar_date is duplicated.", "Keep one calendar row per date or split by exchange carefully.", calendar_date))

    keys = [(_clean(row.get("exchange")), _parse_date(row.get("calendar_date"))) for row in rows]
    for (exchange, calendar_date), count in Counter(keys).items():
        if exchange and calendar_date and count > 1:
            issues.append(_issue("error", "trade_calendar", "duplicate_exchange_calendar_date", None, "calendar_date", "exchange + calendar_date is duplicated.", "Keep one row per exchange and date.", calendar_date))

    open_dates: list[date] = []
    for row in rows:
        calendar_date = _parse_date(row.get("calendar_date"))
        previous_open = _parse_date(row.get("previous_open_date"))
        next_open = _parse_date(row.get("next_open_date"))
        if calendar_date is None:
            continue
        if previous_open is not None and previous_open >= calendar_date:
            issues.append(_issue("error", "trade_calendar", "previous_open_date_not_before", None, "previous_open_date", "previous_open_date is not earlier than calendar_date.", "Check the trading calendar neighbor date.", calendar_date))
        if next_open is not None and next_open <= calendar_date:
            issues.append(_issue("error", "trade_calendar", "next_open_date_not_after", None, "next_open_date", "next_open_date is not later than calendar_date.", "Check the trading calendar neighbor date.", calendar_date))
        if _parse_bool(row.get("is_open")) is True:
            open_dates.append(calendar_date)

    for previous, current in zip(sorted(set(open_dates)), sorted(set(open_dates))[1:]):
        if (current - previous).days > 7:
            issues.append(_issue("warning", "trade_calendar", "large_open_date_gap", None, "calendar_date", "Open date sequence has a large natural-day gap.", "Confirm whether the gap is a holiday or missing calendar data.", current))
            break
    return issues


def check_stock_status_history(
    rows: list[dict[str, str]],
    stock_rows: list[dict[str, str]],
    target_date: date | None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    stock_codes = {_clean(row.get("ts_code")) for row in stock_rows if _clean(row.get("ts_code"))}
    rows_by_stock: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        ts_code = _clean(row.get("ts_code"))
        rows_by_stock[ts_code].append(row)
        start = _parse_date(row.get("effective_start"))
        end = _parse_date(row.get("effective_end"))
        if ts_code and ts_code not in stock_codes:
            issues.append(_issue("error", "stock_status_history", "unknown_ts_code", ts_code, "ts_code", "ts_code does not exist in stock_master.", "Add the stock to stock_master or remove the orphan status row."))
        if start is not None and end is not None and end < start:
            issues.append(_issue("error", "stock_status_history", "effective_end_before_start", ts_code, "effective_end", "effective_end is earlier than effective_start.", "Fix the status effective interval.", start))
        board = _clean(row.get("board"))
        conflict = _prefix_board_conflict(ts_code, board)
        if conflict is not None:
            issues.append(_issue("warning", "stock_status_history", "board_prefix_conflict", ts_code, "board", conflict, "Check board history against ts_code prefix.", start))
        if not _clean(row.get("available_at")):
            issues.append(_issue("warning", "stock_status_history", "missing_available_at", ts_code, "available_at", "available_at is missing for status history.", "Populate source-visible time for point-in-time audits.", start))

    for ts_code, stock_status_rows in rows_by_stock.items():
        parsed = [
            (_parse_date(row.get("effective_start")), _parse_date(row.get("effective_end")), row)
            for row in stock_status_rows
        ]
        valid = sorted((start, end, row) for start, end, row in parsed if start is not None)
        for _, (start, end, row) in enumerate(valid):
            for other_start, other_end, _ in valid:
                if other_start <= start:
                    continue
                if end is None or other_start <= end:
                    issues.append(_issue("warning", "stock_status_history", "overlapping_status_interval", ts_code, "effective_start", "Status history intervals overlap.", "Keep one effective status row per stock and date, or document source priority.", other_start))
                    break
            else:
                continue
            break

    if target_date is not None:
        stock_by_code = {_clean(row.get("ts_code")): row for row in stock_rows}
        for ts_code, stock_row in stock_by_code.items():
            status_row = _status_on(rows_by_stock.get(ts_code, []), target_date)
            if status_row is None:
                continue
            for field in ("board", "industry", "is_st", "is_star_st", "is_suspended", "is_delisting_risk"):
                current_value = _clean(stock_row.get(field)).lower()
                history_value = _clean(status_row.get(field)).lower()
                if current_value and history_value and current_value != history_value:
                    issues.append(_issue("info", "stock_status_history", "stock_master_history_mismatch", ts_code, field, "stock_master current-state field differs from status history on target date.", "Prefer stock_status_history for historical point-in-time research.", target_date))
                    break
    return issues


def check_adjustment_factor(
    rows: list[dict[str, str]],
    stock_rows: list[dict[str, str]],
    daily_rows: list[dict[str, str]],
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    stock_codes = {_clean(row.get("ts_code")) for row in stock_rows if _clean(row.get("ts_code"))}
    daily_keys = {(_clean(row.get("ts_code")), _parse_date(row.get("trade_date"))) for row in daily_rows}
    factor_keys: set[tuple[str, date | None, str]] = set()
    keys = [(_clean(row.get("ts_code")), _parse_date(row.get("trade_date")), _clean(row.get("adj_type"))) for row in rows]
    for key, count in Counter(keys).items():
        ts_code, trade_date, _ = key
        if ts_code and trade_date and count > 1:
            issues.append(_issue("warning", "adjustment_factor", "duplicate_adjustment_factor", ts_code, "trade_date", "ts_code + trade_date + adj_type is duplicated.", "Keep one factor per stock, date, and adjustment type.", trade_date))
    for row in rows:
        ts_code = _clean(row.get("ts_code"))
        trade_date = _parse_date(row.get("trade_date"))
        adj_factor = _parse_float(row.get("adj_factor"))
        adj_type = _clean(row.get("adj_type"))
        factor_keys.add((ts_code, trade_date, adj_type))
        if ts_code and ts_code not in stock_codes:
            issues.append(_issue("error", "adjustment_factor", "unknown_ts_code", ts_code, "ts_code", "ts_code does not exist in stock_master.", "Add the stock to stock_master or remove the orphan factor row.", trade_date))
        if adj_factor is not None and adj_factor <= 0:
            issues.append(_issue("error", "adjustment_factor", "nonpositive_adj_factor", ts_code, "adj_factor", "adj_factor must be greater than zero.", "Fix the adjustment factor source row.", trade_date))

    daily_codes = sorted({ts_code for ts_code, trade_date in daily_keys if ts_code and trade_date})
    factor_codes = {ts_code for ts_code, trade_date, adj_type in factor_keys if ts_code and trade_date and adj_type == "qfq"}
    for ts_code in daily_codes:
        if ts_code not in factor_codes:
            issues.append(_issue("info", "adjustment_factor", "missing_qfq_factor_for_stock", ts_code, "adj_factor", "daily_bar exists but qfq adjustment_factor has no rows for this stock.", "Populate qfq factors before building adjusted daily bars."))
    return issues


def check_corporate_action(rows: list[dict[str, str]], stock_rows: list[dict[str, str]]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    stock_codes = {_clean(row.get("ts_code")) for row in stock_rows if _clean(row.get("ts_code"))}
    keys = [(_clean(row.get("ts_code")), _parse_date(row.get("action_date")), _clean(row.get("action_type"))) for row in rows]
    for (ts_code, action_date, _), count in Counter(keys).items():
        if ts_code and action_date and count > 1:
            issues.append(_issue("warning", "corporate_action", "duplicate_corporate_action", ts_code, "action_date", "ts_code + action_date + action_type is duplicated.", "Deduplicate corporate action rows.", action_date))
    for row in rows:
        ts_code = _clean(row.get("ts_code"))
        action_date = _parse_date(row.get("action_date"))
        publish_date = _parse_date(row.get("publish_date"))
        if ts_code and ts_code not in stock_codes:
            issues.append(_issue("error", "corporate_action", "unknown_ts_code", ts_code, "ts_code", "ts_code does not exist in stock_master.", "Add the stock to stock_master or remove the orphan action row.", action_date))
        if publish_date is not None and action_date is not None and (publish_date - action_date).days > 30:
            issues.append(_issue("info", "corporate_action", "publish_date_far_after_action_date", ts_code, "publish_date", "publish_date is far after action_date.", "Confirm date semantics for this corporate action.", action_date))
        if not _clean(row.get("available_at")):
            issues.append(_issue("warning", "corporate_action", "missing_available_at", ts_code, "available_at", "available_at is missing for corporate action.", "Populate source-visible time for point-in-time audits.", action_date))
        for field in ("cash_dividend", "bonus_share_ratio", "transfer_share_ratio", "rights_issue_ratio"):
            value = _parse_float(row.get(field))
            if value is not None and value < 0:
                issues.append(_issue("error", "corporate_action", f"negative_{field}", ts_code, field, f"{field} must not be negative.", "Fix the corporate action numeric field.", action_date))
    return issues


def _status_on(rows: list[dict[str, str]], on_date: date) -> dict[str, str] | None:
    matches = []
    for row in rows:
        start = _parse_date(row.get("effective_start"))
        end = _parse_date(row.get("effective_end"))
        if start is not None and start <= on_date and (end is None or on_date <= end):
            matches.append((start, row))
    return sorted(matches, key=lambda item: item[0])[-1][1] if matches else None


def _prefix_board_conflict(ts_code: str, board: str) -> str | None:
    symbol = ts_code.split(".")[0]
    if symbol.startswith("300") and board != "chinext":
        return "300 prefix usually indicates ChiNext, but board is not chinext."
    if symbol.startswith("688") and board != "star":
        return "688 prefix usually indicates STAR Market, but board is not star."
    if symbol.startswith("920") and board != "bse":
        return "920 prefix usually indicates BSE, but board is not bse."
    if symbol.startswith(("600", "601", "603", "605")) and board != "main":
        return "600/601/603/605 prefix usually indicates SSE main board, but board is not main."
    if symbol.startswith(("000", "001", "002")) and board != "main":
        return "000/001/002 prefix usually indicates SZSE main board, but board is not main."
    return None


def _issue(
    severity: str,
    dataset_name: str,
    issue_type: str,
    ts_code: str | None,
    field_name: str | None,
    message: str,
    recommendation: str,
    trade_date: date | None = None,
) -> QualityIssue:
    return QualityIssue(
        severity=severity,
        dataset_name=dataset_name,
        issue_type=issue_type,
        ts_code=ts_code or None,
        trade_date=trade_date,
        field_name=field_name,
        message=message,
        recommendation=recommendation,
    )


def _parse_date(value: Any) -> date | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_float(value: Any) -> float | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_bool(value: Any) -> bool | None:
    text = _clean(value).lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()
