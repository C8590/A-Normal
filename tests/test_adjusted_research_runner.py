from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.adjusted_research import AdjustedResearchRunner


def test_adjusted_research_runner_sample_data(tmp_path: Path) -> None:
    output_dir = tmp_path / "adjusted_research"

    report = AdjustedResearchRunner(
        target_date=date(2026, 3, 20),
        start_date=date(2026, 1, 5),
        end_date=date(2026, 3, 20),
        data_dir=Path("data/sample/ashare_alpha"),
        config_dir=Path("configs/ashare_alpha"),
        output_dir=output_dir,
    ).run()

    assert report.status in {"SUCCESS", "PARTIAL"}
    assert len(report.factor_comparisons) == 2
    assert len(report.backtest_comparisons) == 2
    assert (output_dir / "adjusted_research_report.json").exists()
    assert (output_dir / "adjusted_research_report.md").exists()
    assert (output_dir / "adjusted_research_summary.csv").exists()
    assert any("INFO: 当前样例无交易" in item for item in report.warning_items)
