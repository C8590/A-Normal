from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from ashare_alpha.quality.models import QualityIssue


EXCHANGES = {"sse", "szse", "bse"}
BOARDS = {"main", "chinext", "star", "bse"}
EVENT_DIRECTIONS = {"positive", "negative", "neutral"}
EVENT_RISK_LEVELS = {"low", "medium", "high"}
FINANCIAL_NUMERIC_FIELDS = [
    "revenue_yoy",
    "profit_yoy",
    "net_profit_yoy",
    "roe",
    "gross_margin",
    "debt_to_asset",
    "operating_cashflow_to_profit",
    "goodwill_to_equity",
]


def check_stock_master(rows: list[dict[str, str]]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    ts_codes = [_clean(row.get("ts_code")) for row in rows]
    for ts_code, count in Counter(ts_codes).items():
        if ts_code and count > 1:
            issues.append(_issue("error", "stock_master", "duplicate_ts_code", ts_code, "ts_code", "股票代码重复。", "检查 stock_master.csv 并保留唯一 ts_code。"))

    for row in rows:
        ts_code = _clean(row.get("ts_code"))
        symbol = _clean(row.get("symbol"))
        name = _clean(row.get("name"))
        exchange = _clean(row.get("exchange")).lower()
        board = _clean(row.get("board")).lower()
        list_date = _parse_date(row.get("list_date"))
        delist_date = _parse_date(row.get("delist_date"))
        if not symbol:
            issues.append(_issue("error", "stock_master", "missing_symbol", ts_code, "symbol", "symbol 为空。", "补充证券代码简称字段。"))
        if not name:
            issues.append(_issue("error", "stock_master", "missing_name", ts_code, "name", "name 为空。", "补充股票名称。"))
        if exchange not in EXCHANGES:
            issues.append(_issue("error", "stock_master", "invalid_exchange", ts_code, "exchange", "exchange 不在允许范围内。", "使用 sse、szse 或 bse。"))
        if board not in BOARDS:
            issues.append(_issue("error", "stock_master", "invalid_board", ts_code, "board", "board 不在允许范围内。", "使用 main、chinext、star 或 bse。"))
        if list_date is None:
            issues.append(_issue("error", "stock_master", "missing_list_date", ts_code, "list_date", "list_date 缺失或格式错误。", "补充 YYYY-MM-DD 格式上市日期。"))
        if list_date is not None and delist_date is not None and delist_date < list_date:
            issues.append(_issue("error", "stock_master", "delist_before_list", ts_code, "delist_date", "delist_date 早于 list_date。", "检查上市和退市日期。"))
        conflict = _prefix_board_conflict(ts_code, exchange, board)
        if conflict:
            issues.append(_issue("warning", "stock_master", "board_prefix_conflict", ts_code, "board", conflict, "核对 board、exchange 与 ts_code 前缀是否匹配。"))
    return issues


def check_daily_bar(rows: list[dict[str, str]], stock_codes: set[str]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    keys = [(_clean(row.get("ts_code")), _parse_date(row.get("trade_date"))) for row in rows]
    for (ts_code, trade_date), count in Counter(keys).items():
        if ts_code and trade_date and count > 1:
            issues.append(_issue("error", "daily_bar", "duplicate_daily_bar", ts_code, None, "ts_code + trade_date 重复。", "检查 daily_bar.csv 并保留唯一日线记录。", trade_date))

    dates_by_stock: dict[str, list[date]] = defaultdict(list)
    for row in rows:
        ts_code = _clean(row.get("ts_code"))
        trade_date = _parse_date(row.get("trade_date"))
        if ts_code and ts_code not in stock_codes:
            issues.append(_issue("error", "daily_bar", "unknown_ts_code", ts_code, "ts_code", "daily_bar 中的 ts_code 不存在于 stock_master。", "先补齐 stock_master 或删除无法关联的日线。", trade_date))
        if ts_code and trade_date:
            dates_by_stock[ts_code].append(trade_date)

        prices = {field: _parse_float(row.get(field)) for field in ("open", "high", "low", "close", "pre_close")}
        for field, value in prices.items():
            if value is not None and value < 0:
                issues.append(_issue("error", "daily_bar", "negative_price", ts_code, field, f"{field} 为负数。", "检查行情价格字段。", trade_date))
        high, low, open_, close, pre_close = (prices["high"], prices["low"], prices["open"], prices["close"], prices["pre_close"])
        if high is not None and low is not None and high < low:
            issues.append(_issue("error", "daily_bar", "high_below_low", ts_code, "high", "high 小于 low。", "检查日线最高价和最低价。", trade_date))
        if high is not None and ((open_ is not None and high < open_) or (close is not None and high < close)):
            issues.append(_issue("error", "daily_bar", "high_below_open_or_close", ts_code, "high", "high 小于 open 或 close。", "检查日线价格形态。", trade_date))
        if low is not None and ((open_ is not None and low > open_) or (close is not None and low > close)):
            issues.append(_issue("error", "daily_bar", "low_above_open_or_close", ts_code, "low", "low 大于 open 或 close。", "检查日线价格形态。", trade_date))

        amount = _parse_float(row.get("amount"))
        volume = _parse_float(row.get("volume"))
        is_trading = _parse_bool(row.get("is_trading"))
        if is_trading is True and amount is not None and amount <= 0:
            issues.append(_issue("warning", "daily_bar", "trading_with_nonpositive_amount", ts_code, "amount", "is_trading=true 但 amount<=0。", "核对成交额或停复牌状态。", trade_date))
        if is_trading is False and amount is not None and amount > 0:
            issues.append(_issue("warning", "daily_bar", "not_trading_with_positive_amount", ts_code, "amount", "is_trading=false 但 amount>0。", "核对成交额和交易状态。", trade_date))
        if is_trading is True and volume is not None and volume <= 0:
            issues.append(_issue("warning", "daily_bar", "trading_with_zero_volume", ts_code, "volume", "is_trading=true 但 volume 为 0。", "核对成交量。", trade_date))
        if close is not None and pre_close not in (None, 0) and abs(close / pre_close - 1) > 0.30:
            issues.append(_issue("warning", "daily_bar", "extreme_daily_return", ts_code, "close", "close 相对 pre_close 单日涨跌幅绝对值超过 30%。", "核对复权、停复牌或价格字段。", trade_date))

        limit_up = _parse_float(row.get("limit_up"))
        limit_down = _parse_float(row.get("limit_down"))
        if limit_up is not None and limit_down is not None and limit_up < limit_down:
            issues.append(_issue("error", "daily_bar", "limit_up_below_limit_down", ts_code, "limit_up", "limit_up 小于 limit_down。", "检查涨跌停价格字段。", trade_date))
        if close is not None and limit_up is not None and close > limit_up + 0.01:
            issues.append(_issue("warning", "daily_bar", "close_above_limit_up", ts_code, "close", "close 明显高于 limit_up。", "核对收盘价、涨停价或复权口径。", trade_date))
        if close is not None and limit_down is not None and close < limit_down - 0.01:
            issues.append(_issue("warning", "daily_bar", "close_below_limit_down", ts_code, "close", "close 明显低于 limit_down。", "核对收盘价、跌停价或复权口径。", trade_date))

    for ts_code, dates in dates_by_stock.items():
        unique_dates = sorted(set(dates))
        if len(unique_dates) < 60:
            issues.append(_issue("warning", "daily_bar", "few_trading_records", ts_code, "trade_date", "单只股票交易记录少于 60 条。", "检查样本区间或该股票是否缺少行情。"))
        for previous, current in zip(unique_dates, unique_dates[1:]):
            if (current - previous).days > 10:
                issues.append(_issue("warning", "daily_bar", "large_date_gap", ts_code, "trade_date", "单只股票日线日期存在超过 10 个自然日的断档。", "检查停牌、节假日或缺失行情。", current))
                break
    return issues


def check_financial_summary(rows: list[dict[str, str]], stock_codes: set[str]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    keys = [(_clean(row.get("ts_code")), _parse_date(row.get("report_date"))) for row in rows]
    for (ts_code, report_date), count in Counter(keys).items():
        if ts_code and report_date and count > 1:
            issues.append(_issue("warning", "financial_summary", "duplicate_financial_report", ts_code, "report_date", "同一 ts_code + report_date 重复。", "核对财务表重复记录。"))

    for row in rows:
        ts_code = _clean(row.get("ts_code"))
        if ts_code and ts_code not in stock_codes:
            issues.append(_issue("error", "financial_summary", "unknown_ts_code", ts_code, "ts_code", "financial_summary 中的 ts_code 不存在于 stock_master。", "先补齐 stock_master 或删除无法关联的财务记录。"))
        report_date = _parse_date(row.get("report_date"))
        publish_date = _parse_date(row.get("publish_date"))
        if report_date is not None and publish_date is not None and publish_date < report_date:
            issues.append(_issue("error", "financial_summary", "publish_before_report", ts_code, "publish_date", "publish_date 早于 report_date。", "检查财务披露日期。"))
        if _all_blank(row, FINANCIAL_NUMERIC_FIELDS):
            issues.append(_issue("warning", "financial_summary", "all_financial_fields_missing", ts_code, None, "财务数值字段全部为空。", "补齐财务指标或确认该记录是否应保留。"))
        for field, lower, upper in [
            ("debt_to_asset", 0, 1.5),
            ("goodwill_to_equity", 0, 5),
            ("gross_margin", -1, 1),
            ("roe", -5, 5),
        ]:
            value = _parse_float(row.get(field))
            if value is not None and not (lower <= value <= upper):
                issues.append(_issue("warning", "financial_summary", f"extreme_{field}", ts_code, field, f"{field} 超出常见范围。", "核对财务单位和原始字段。"))
        value = _parse_float(row.get("operating_cashflow_to_profit"))
        if value is not None and abs(value) > 20:
            issues.append(_issue("warning", "financial_summary", "extreme_operating_cashflow_to_profit", ts_code, "operating_cashflow_to_profit", "operating_cashflow_to_profit 绝对值超过 20。", "核对财务单位和异常值。"))
    return issues


def check_announcement_event(
    rows: list[dict[str, str]],
    stock_codes: set[str],
    daily_bar_max_date: date | None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    keys = [(_clean(row.get("ts_code")), _parse_datetime(row.get("event_time")), _clean(row.get("title"))) for row in rows]
    for (ts_code, event_time, title), count in Counter(keys).items():
        if ts_code and event_time and title and count > 1:
            issues.append(_issue("warning", "announcement_event", "duplicate_announcement_event", ts_code, "title", "同一 ts_code + event_time + title 重复。", "核对公告事件重复记录。"))

    for row in rows:
        ts_code = _clean(row.get("ts_code"))
        event_time = _parse_datetime(row.get("event_time"))
        if ts_code and ts_code not in stock_codes:
            issues.append(_issue("error", "announcement_event", "unknown_ts_code", ts_code, "ts_code", "announcement_event 中的 ts_code 不存在于 stock_master。", "先补齐 stock_master 或删除无法关联的公告记录。"))
        if not _clean(row.get("title")):
            issues.append(_issue("error", "announcement_event", "missing_title", ts_code, "title", "title 为空。", "补充公告标题。"))
        if not _clean(row.get("source")):
            issues.append(_issue("warning", "announcement_event", "missing_source", ts_code, "source", "source 为空。", "补充公告来源。"))
        strength = _parse_float(row.get("event_strength"))
        if strength is None or not (0 <= strength <= 1):
            issues.append(_issue("error", "announcement_event", "invalid_event_strength", ts_code, "event_strength", "event_strength 不在 0 到 1 之间。", "将事件强度标准化到 0-1。"))
        if _clean(row.get("event_direction")) not in EVENT_DIRECTIONS:
            issues.append(_issue("error", "announcement_event", "invalid_event_direction", ts_code, "event_direction", "event_direction 非法。", "使用 positive、negative 或 neutral。"))
        if _clean(row.get("event_risk_level")) not in EVENT_RISK_LEVELS:
            issues.append(_issue("error", "announcement_event", "invalid_event_risk_level", ts_code, "event_risk_level", "event_risk_level 非法。", "使用 low、medium 或 high。"))
        if event_time is not None and daily_bar_max_date is not None and (event_time.date() - daily_bar_max_date).days > 30:
            issues.append(_issue("warning", "announcement_event", "event_time_far_after_daily_bar", ts_code, "event_time", "event_time 明显晚于 daily_bar 最大日期。", "核对公告数据批次和行情数据批次是否匹配。"))
    return issues


def check_cross_table_coverage(
    stock_rows: list[dict[str, str]],
    daily_rows: list[dict[str, str]],
    financial_rows: list[dict[str, str]],
    announcement_rows: list[dict[str, str]],
    target_date: date | None,
) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    stock_codes = {_clean(row.get("ts_code")) for row in stock_rows if _clean(row.get("ts_code"))}
    daily_codes = {_clean(row.get("ts_code")) for row in daily_rows if _clean(row.get("ts_code"))}
    financial_codes = {_clean(row.get("ts_code")) for row in financial_rows if _clean(row.get("ts_code"))}
    announcement_codes = {_clean(row.get("ts_code")) for row in announcement_rows if _clean(row.get("ts_code"))}
    for ts_code in sorted(stock_codes - daily_codes):
        issues.append(_issue("warning", "cross_table", "stock_without_daily_bar", ts_code, None, "stock_master 中该股票完全没有 daily_bar。", "补齐行情数据或从研究范围中排除。"))
    for ts_code in sorted(stock_codes - financial_codes):
        issues.append(_issue("info", "cross_table", "stock_without_financial_summary", ts_code, None, "stock_master 中该股票没有 financial_summary。", "如果后续使用财务因子，应补齐财务数据。"))
    for ts_code in sorted(stock_codes - announcement_codes):
        issues.append(_issue("info", "cross_table", "stock_without_announcement_event", ts_code, None, "stock_master 中该股票没有 announcement_event。", "如无公告事件可接受；如接入真实数据，应确认覆盖范围。"))

    daily_dates = sorted({_parse_date(row.get("trade_date")) for row in daily_rows if _parse_date(row.get("trade_date"))})
    if daily_dates:
        span_days = (daily_dates[-1] - daily_dates[0]).days + 1
        if span_days < 120 or len(daily_dates) < 60:
            issues.append(_issue("warning", "daily_bar", "daily_bar_range_too_short", None, "trade_date", "daily_bar 日期范围过短。", "建议提供至少 120 个自然日或 60 个交易日记录。"))
        if target_date is not None and daily_dates[-1] < target_date:
            issues.append(_issue("warning", "daily_bar", "daily_bar_max_before_target_date", None, "trade_date", "daily_bar 最大日期早于目标研究日期。", "补齐目标日期前后的行情数据。", daily_dates[-1]))
        publish_dates = [_parse_date(row.get("publish_date")) for row in financial_rows]
        valid_publish_dates = [item for item in publish_dates if item is not None]
        if valid_publish_dates and all(item > daily_dates[-1] for item in valid_publish_dates):
            issues.append(_issue("warning", "financial_summary", "financial_publish_after_daily_range", None, "publish_date", "financial_summary publish_date 全部晚于 daily_bar 最大日期。", "确认财务数据批次和行情数据批次是否匹配。"))
    return issues


def _prefix_board_conflict(ts_code: str, exchange: str, board: str) -> str | None:
    symbol = ts_code.split(".")[0]
    if symbol.startswith("300") and board != "chinext":
        return "300 开头通常为创业板，当前 board 不是 chinext。"
    if symbol.startswith("688") and board != "star":
        return "688 开头通常为科创板，当前 board 不是 star。"
    if symbol.startswith("920") and board != "bse":
        return "920 开头通常为北交所，当前 board 不是 bse。"
    if symbol.startswith(("600", "601", "603", "605")) and (exchange != "sse" or board != "main"):
        return "600/601/603/605 开头通常为上交所主板，当前 exchange/board 可能不匹配。"
    if symbol.startswith(("000", "001", "002")) and (exchange != "szse" or board != "main"):
        return "000/001/002 开头通常为深交所主板，当前 exchange/board 可能不匹配。"
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


def _parse_datetime(value: Any) -> datetime | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
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


def _all_blank(row: dict[str, str], fields: list[str]) -> bool:
    return all(not _clean(row.get(field)) for field in fields)
