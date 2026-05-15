from __future__ import annotations

from pathlib import Path

from ashare_alpha.dashboard import DashboardScanner
from dashboard_helpers import write_dashboard_fixture


def test_scanner_identifies_all_supported_artifacts(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)

    index = DashboardScanner(paths["outputs"]).scan()

    counts = index.artifacts_by_type
    assert counts["pipeline"] == 1
    assert counts["backtest"] == 1
    assert counts["sweep"] == 1
    assert counts["walkforward"] == 1
    assert counts["experiment"] == 1
    assert counts["candidate_selection"] == 1
    assert counts["quality_report"] == 1
    assert counts["leakage_audit"] == 1
    assert counts["security_scan"] == 1
    assert counts["probability_model"] == 1
    assert counts["unknown"] == 1


def test_scanner_corrupt_json_does_not_fail_global_scan(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)

    index = DashboardScanner(paths["outputs"]).scan()
    unknown = [artifact for artifact in index.artifacts if artifact.artifact_type == "unknown"]

    assert len(unknown) == 1
    assert "error" in unknown[0].summary
