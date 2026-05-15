from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from ashare_alpha.realdata import (
    RealDataOfflineDrillResult,
    RealDataOfflineDrillStep,
    load_realdata_offline_drill_result,
    save_realdata_offline_drill_artifacts,
)


def test_drill_result_saves_loads_and_renders(tmp_path: Path) -> None:
    started = datetime.now()
    result = RealDataOfflineDrillResult(
        drill_id="drill_test",
        drill_name="test_drill",
        generated_at=started,
        source_name="tushare_like_offline",
        data_version="test_v1",
        target_date=date(2026, 3, 20),
        status="SUCCESS",
        output_dir=str(tmp_path),
        steps=[
            RealDataOfflineDrillStep(
                name="validate_data",
                status="SUCCESS",
                started_at=started,
                finished_at=started,
                duration_seconds=0.0,
                output_paths=[str(tmp_path / "validation_report.json")],
                summary={"passed": True},
            )
        ],
        materialized_data_dir=str(tmp_path / "materialized"),
        imported_data_dir=str(tmp_path / "imports"),
        pipeline_output_dir=str(tmp_path / "pipeline"),
        frontend_output_dir=str(tmp_path / "frontend"),
        dashboard_output_dir=str(tmp_path / "dashboard"),
        experiment_id="exp_test",
        summary={"pipeline": {"buy_count": 1, "watch_count": 2, "block_count": 3}},
    )

    save_realdata_offline_drill_artifacts(result, tmp_path)
    loaded = load_realdata_offline_drill_result(tmp_path / "drill_result.json")

    assert loaded.drill_id == "drill_test"
    assert (tmp_path / "drill_report.md").exists()
    assert (tmp_path / "step_summary.csv").exists()
    assert "Real Data Offline Drill Report" in (tmp_path / "drill_report.md").read_text(encoding="utf-8")
