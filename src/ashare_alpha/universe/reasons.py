from __future__ import annotations

from enum import StrEnum


class ExcludeReason(StrEnum):
    BOARD_NOT_ALLOWED = "BOARD_NOT_ALLOWED"
    BOARD_EXCLUDED = "BOARD_EXCLUDED"
    IS_ST = "IS_ST"
    IS_STAR_ST = "IS_STAR_ST"
    DELISTING_RISK = "DELISTING_RISK"
    SUSPENDED = "SUSPENDED"
    LISTING_DAYS_TOO_SHORT = "LISTING_DAYS_TOO_SHORT"
    INSUFFICIENT_DAILY_BARS = "INSUFFICIENT_DAILY_BARS"
    LOW_AVG_AMOUNT_20D = "LOW_AVG_AMOUNT_20D"
    TOO_EXPENSIVE_FOR_CAPITAL = "TOO_EXPENSIVE_FOR_CAPITAL"
    RECENT_NEGATIVE_EVENT = "RECENT_NEGATIVE_EVENT"
    MISSING_LATEST_BAR = "MISSING_LATEST_BAR"
    NOT_TRADING_ON_DATE = "NOT_TRADING_ON_DATE"


REASON_TEXT: dict[ExcludeReason, str] = {
    ExcludeReason.BOARD_NOT_ALLOWED: "所属板块不在第一版允许范围内",
    ExcludeReason.BOARD_EXCLUDED: "所属板块在第一版排除范围内",
    ExcludeReason.IS_ST: "ST 股票，第一版禁止进入股票池",
    ExcludeReason.IS_STAR_ST: "*ST 股票，第一版禁止进入股票池",
    ExcludeReason.DELISTING_RISK: "存在退市风险，第一版禁止进入股票池",
    ExcludeReason.SUSPENDED: "股票处于停牌状态，第一版禁止进入股票池",
    ExcludeReason.LISTING_DAYS_TOO_SHORT: "上市天数低于配置要求",
    ExcludeReason.INSUFFICIENT_DAILY_BARS: "近 20 日行情数据不足",
    ExcludeReason.LOW_AVG_AMOUNT_20D: "近 20 日平均成交额低于配置阈值",
    ExcludeReason.TOO_EXPENSIVE_FOR_CAPITAL: "1 手金额超过当前本金允许的单票上限",
    ExcludeReason.RECENT_NEGATIVE_EVENT: "近期存在负面公告或高风险事件",
    ExcludeReason.MISSING_LATEST_BAR: "目标交易日缺少行情数据",
    ExcludeReason.NOT_TRADING_ON_DATE: "目标交易日不可交易",
}


def reason_text(reason: ExcludeReason | str) -> str:
    return REASON_TEXT[ExcludeReason(reason)]


def join_reason_text(reasons: list[ExcludeReason | str]) -> str:
    return "；".join(reason_text(reason) for reason in reasons)
