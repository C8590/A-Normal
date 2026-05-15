from __future__ import annotations

from ashare_alpha.data import StockMaster
from ashare_alpha.scoring import compute_industry_strength_scores
from tests_support import factor


def test_industry_average_momentum_is_ranked() -> None:
    stocks = [
        _stock("600001.SH", "tech"),
        _stock("600002.SH", "tech"),
        _stock("600003.SH", "bank"),
        _stock("600004.SH", "bank"),
    ]
    scores = compute_industry_strength_scores(
        stocks,
        [
            factor("600001.SH", momentum_20d=0.10),
            factor("600002.SH", momentum_20d=0.08),
            factor("600003.SH", momentum_20d=-0.02),
            factor("600004.SH", momentum_20d=-0.01),
        ],
    )

    assert scores["600001.SH"].score > scores["600003.SH"].score


def test_missing_industry_returns_50() -> None:
    scores = compute_industry_strength_scores([_stock("600001.SH", None)], [factor("600001.SH")])

    assert scores["600001.SH"].score == 50


def test_insufficient_industry_sample_returns_50() -> None:
    scores = compute_industry_strength_scores([_stock("600001.SH", "tech")], [factor("600001.SH")])

    assert scores["600001.SH"].score == 50


def _stock(ts_code: str, industry: str | None) -> StockMaster:
    return StockMaster(
        ts_code=ts_code,
        symbol=ts_code[:6],
        name=ts_code,
        exchange="sse",
        board="main",
        industry=industry,
        list_date="2010-01-01",
        delist_date=None,
        is_st=False,
        is_star_st=False,
        is_suspended=False,
        is_delisting_risk=False,
    )
