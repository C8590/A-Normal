from __future__ import annotations

from ashare_alpha.events import normalize_event_type


def test_known_event_type_returns_directly() -> None:
    assert normalize_event_type("buyback", "股东减持计划") == "buyback"


def test_buyback_keyword() -> None:
    assert normalize_event_type("", "关于股份回购方案的公告") == "buyback"


def test_shareholder_reduce_keyword() -> None:
    assert normalize_event_type("unknown", "控股股东减持计划公告") == "shareholder_reduce"


def test_investigation_keyword() -> None:
    assert normalize_event_type("unknown", "公司收到立案调查通知书") == "investigation"


def test_regulatory_penalty_keyword() -> None:
    assert normalize_event_type("unknown", "关于收到行政处罚决定书的公告") == "regulatory_penalty"


def test_major_contract_keyword() -> None:
    assert normalize_event_type("unknown", "重大合同签署及中标结果公告") == "major_contract"


def test_earnings_positive_keyword() -> None:
    assert normalize_event_type("unknown", "业绩预增及预盈公告") == "earnings_positive"


def test_earnings_negative_keyword() -> None:
    assert normalize_event_type("unknown", "业绩预亏及亏损风险提示") == "earnings_negative"


def test_unknown_when_no_keyword_matches() -> None:
    assert normalize_event_type("unknown", "日常经营情况公告") == "unknown"
