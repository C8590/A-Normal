from __future__ import annotations

from ashare_alpha.events.rules import ALLOWED_EVENT_TYPES


KEYWORD_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("buyback", ("回购", "repurchase", "buyback")),
    ("shareholder_increase", ("增持", "shareholder increase", "increase holding")),
    ("shareholder_reduce", ("减持", "shareholder reduce", "shareholder reduction", "reduce holding")),
    ("regulatory_penalty", ("行政处罚", "监管处罚", "处罚", "regulatory penalty", "penalty")),
    ("investigation", ("立案调查", "立案", "被调查", "调查", "investigation", "investigated")),
    ("litigation", ("诉讼", "仲裁", "litigation", "lawsuit", "arbitration")),
    ("major_contract", ("重大合同", "合同", "中标", "订单", "major contract", "contract", "bid", "order")),
    ("earnings_positive", ("业绩预增", "预盈", "扭亏", "earnings increase", "profit growth")),
    ("earnings_negative", ("业绩预减", "预亏", "亏损", "下修", "earnings decline", "profit warning", "loss warning")),
    ("equity_pledge", ("质押", "equity pledge", "pledge")),
    ("unlock_shares", ("限售股上市", "解禁", "unlock shares", "lock-up expiration")),
)


def normalize_event_type(event_type: str, title: str | None = None) -> str:
    normalized = (event_type or "").strip()
    if normalized in ALLOWED_EVENT_TYPES and normalized != "unknown":
        return normalized

    title_text = (title or "").strip().lower()
    if title_text:
        for candidate, keywords in KEYWORD_RULES:
            if any(keyword.lower() in title_text for keyword in keywords):
                return candidate
    return "unknown"
