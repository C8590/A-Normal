from __future__ import annotations

from pathlib import Path

from ashare_alpha.dashboard import (
    DashboardScanner,
    build_dashboard_summary,
    load_dashboard_index_json,
    load_dashboard_summary_json,
    save_dashboard_index_json,
    save_dashboard_markdown,
    save_dashboard_summary_json,
    save_dashboard_tables,
)
from dashboard_helpers import write_dashboard_fixture


def test_dashboard_storage_outputs_files(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    index = DashboardScanner(paths["outputs"]).scan()
    summary = build_dashboard_summary(index)
    output_dir = tmp_path / "dashboard"

    save_dashboard_index_json(index, output_dir / "dashboard_index.json")
    save_dashboard_summary_json(summary, output_dir / "dashboard_summary.json")
    save_dashboard_markdown(index, summary, output_dir / "dashboard.md")
    save_dashboard_tables(index, summary, output_dir / "dashboard_tables")

    assert load_dashboard_index_json(output_dir / "dashboard_index.json").artifact_count == index.artifact_count
    assert load_dashboard_summary_json(output_dir / "dashboard_summary.json").summary_text
    assert "研究 Dashboard" in (output_dir / "dashboard.md").read_text(encoding="utf-8")
    assert (output_dir / "dashboard_tables" / "artifacts.csv").exists()
    assert (output_dir / "dashboard_tables" / "recent_experiments.csv").exists()
    assert (output_dir / "dashboard_tables" / "top_candidates.csv").exists()
    assert (output_dir / "dashboard_tables" / "warning_items.csv").exists()
