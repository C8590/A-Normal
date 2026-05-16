from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.dashboard import DashboardScanner, build_dashboard_summary, render_dashboard_markdown


def test_dashboard_scans_adjusted_research_artifact(tmp_path: Path) -> None:
    report_path = tmp_path / "outputs" / "adjusted_research" / "run_1" / "adjusted_research_report.json"
    _write_adjusted_report(report_path)

    index = DashboardScanner(tmp_path / "outputs").scan()
    summary = build_dashboard_summary(index)
    markdown = render_dashboard_markdown(index, summary)

    assert index.artifacts_by_type["adjusted_research"] == 1
    assert summary.latest_adjusted_research is not None
    assert summary.latest_adjusted_research.summary["warning_count"] == 1
    assert any(item["artifact_type"] == "adjusted_research" for item in summary.warning_items)
    assert "Latest Adjusted Research" in markdown


def _write_adjusted_report(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "report_id": "adjusted_research_test",
                "generated_at": "2026-05-16T12:00:00",
                "data_dir": "data/sample/ashare_alpha",
                "config_dir": "configs/ashare_alpha",
                "target_date": "2026-03-20",
                "start_date": "2026-01-05",
                "end_date": "2026-03-20",
                "status": "PARTIAL",
                "steps": [],
                "factor_comparisons": [{}, {}],
                "backtest_comparisons": [{}, {}],
                "warning_items": ["INFO: sample"],
                "output_dir": str(path.parent),
                "summary": "ok",
            }
        ),
        encoding="utf-8",
    )
