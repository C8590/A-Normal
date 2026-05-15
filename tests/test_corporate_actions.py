from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.data.realism import CorporateActionSeries, OptionalRealismDataLoader


def test_corporate_action_series_queries_actions() -> None:
    bundle = OptionalRealismDataLoader(Path("data/sample/ashare_alpha")).load_all()
    series = CorporateActionSeries(bundle.corporate_actions)

    assert len(series.actions_for_stock("600001.SH")) == 1
    assert len(series.actions_between(date(2026, 2, 1), date(2026, 3, 31))) == 3
    visible = series.actions_visible_on(date(2026, 3, 5))
    assert {item.ts_code for item in visible} == {"600001.SH", "600002.SH"}
