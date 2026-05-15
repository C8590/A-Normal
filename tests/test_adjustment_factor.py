from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.data.realism import AdjustmentFactorSeries, OptionalRealismDataLoader


def test_adjustment_factor_series_queries_factor_and_coverage() -> None:
    bundle = OptionalRealismDataLoader(Path("data/sample/ashare_alpha")).load_all()
    series = AdjustmentFactorSeries(bundle.adjustment_factors)

    assert series.has_factor("600001.SH", date(2026, 1, 2))
    assert series.get_factor("600001.SH", date(2026, 3, 20)) == 1.02
    coverage = series.factor_coverage("600001.SH")
    assert coverage["row_count"] >= 60
    assert coverage["factor_max"] == 1.02
