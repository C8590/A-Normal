from __future__ import annotations

from pathlib import Path

from ashare_alpha.data.realism import OptionalRealismDataLoader


DATA_DIR = Path("data/sample/ashare_alpha")


def test_optional_realism_loader_missing_files_do_not_fail(tmp_path: Path) -> None:
    bundle = OptionalRealismDataLoader(tmp_path).load_all()

    assert bundle.trade_calendar == []
    assert sorted(bundle.missing_optional_files) == sorted(OptionalRealismDataLoader.FILES.values())


def test_optional_realism_loader_loads_sample_files() -> None:
    bundle = OptionalRealismDataLoader(DATA_DIR).load_all()

    assert len(bundle.trade_calendar) == 90
    assert len(bundle.stock_status_history) >= 12
    assert len(bundle.adjustment_factors) >= 60
    assert len(bundle.corporate_actions) == 3
    assert bundle.missing_optional_files == []
