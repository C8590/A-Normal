from __future__ import annotations

from typing import Final


ALLOWED_EVENT_TYPES: Final[set[str]] = {
    "earnings_positive",
    "earnings_negative",
    "buyback",
    "shareholder_increase",
    "shareholder_reduce",
    "regulatory_penalty",
    "investigation",
    "litigation",
    "major_contract",
    "equity_pledge",
    "unlock_shares",
    "unknown",
}

EVENT_TYPE_TEXT: Final[dict[str, str]] = {
    "earnings_positive": "业绩利好",
    "earnings_negative": "业绩利空",
    "buyback": "回购事件",
    "shareholder_increase": "股东增持",
    "shareholder_reduce": "股东减持",
    "regulatory_penalty": "监管处罚",
    "investigation": "立案调查",
    "litigation": "诉讼仲裁",
    "major_contract": "重大合同",
    "equity_pledge": "股权质押",
    "unlock_shares": "限售解禁",
    "unknown": "未识别公告事件",
}


def event_type_text(event_type: str) -> str:
    return EVENT_TYPE_TEXT.get(event_type, EVENT_TYPE_TEXT["unknown"])


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))
