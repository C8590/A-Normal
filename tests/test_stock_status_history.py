from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.data.realism import OptionalRealismDataLoader, StockStatusHistory


def test_stock_status_history_queries_by_date() -> None:
    bundle = OptionalRealismDataLoader(Path("data/sample/ashare_alpha")).load_all()
    history = StockStatusHistory(bundle.stock_status_history)

    assert history.is_suspended("600005.SH", date(2026, 3, 1)) is False
    assert history.is_suspended("600005.SH", date(2026, 3, 20)) is True
    assert history.is_st("600003.SH", date(2026, 3, 20)) is True
    assert history.board_on("300001.SZ", date(2026, 3, 20)) == "chinext"
    assert history.industry_on("688001.SH", date(2026, 3, 20)) == "semiconductor"
    assert history.listing_status_on("600006.SH", date(2026, 3, 20)) == "delisting_risk"
