from __future__ import annotations

from pathlib import Path

from ashare_alpha.dashboard import DashboardScanner, build_dashboard_summary
from dashboard_helpers import write_dashboard_fixture


def test_dashboard_summary_selects_latest_and_extracts_rows(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    index = DashboardScanner(paths["outputs"]).scan()

    summary = build_dashboard_summary(index)

    assert summary.latest_candidate_selection is not None
    assert summary.top_candidates[0]["candidate_id"] == "c1"
    assert summary.recent_experiments[0]["experiment_id"] == "exp_20260514_000000_abcd1234"


def test_dashboard_summary_collects_warnings(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)

    summary = build_dashboard_summary(DashboardScanner(paths["outputs"]).scan())
    types = {item["artifact_type"] for item in summary.warning_items}

    assert {"quality_report", "leakage_audit", "security_scan", "walkforward", "sweep", "pipeline", "unknown"} <= types


def test_dashboard_summary_text_avoids_forbidden_promises(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)

    summary = build_dashboard_summary(DashboardScanner(paths["outputs"]).scan())

    for forbidden in ("稳赚", "最佳必胜", "保证收益"):
        assert forbidden not in summary.summary_text
    assert "不构成投资建议" in summary.summary_text
