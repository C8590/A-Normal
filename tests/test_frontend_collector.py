from __future__ import annotations

from pathlib import Path

from ashare_alpha.frontend import collect_frontend_data
from dashboard_helpers import write_dashboard_fixture


def test_collector_generates_data_from_outputs(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)

    data = collect_frontend_data(paths["outputs"])

    assert data.summary["artifact_count"] >= 10
    assert data.latest_pipeline is not None
    assert data.latest_backtest is not None
    assert data.top_candidates


def test_collector_empty_outputs_does_not_crash(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs"
    outputs.mkdir()

    data = collect_frontend_data(outputs)

    assert data.summary["artifact_count"] == 0
    assert data.artifacts == []


def test_collector_corrupt_json_enters_warning(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)

    data = collect_frontend_data(paths["outputs"])

    assert any(item.get("artifact_type") == "unknown" for item in data.warning_items)
