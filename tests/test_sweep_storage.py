from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from ashare_alpha.sweeps.models import SweepResult, SweepRunRecord
from ashare_alpha.sweeps.storage import (
    load_sweep_result_json,
    save_metrics_table_csv,
    save_sweep_result_json,
    save_sweep_summary_md,
)


def test_sweep_result_json_round_trips(tmp_path: Path) -> None:
    result = _result(tmp_path)
    path = tmp_path / "sweep_result.json"

    save_sweep_result_json(result, path)
    loaded = load_sweep_result_json(path)

    assert loaded.sweep_id == result.sweep_id


def test_sweep_summary_md_saves(tmp_path: Path) -> None:
    result = _result(tmp_path)
    path = tmp_path / "sweep_summary.md"

    save_sweep_summary_md(result, path)

    assert "# Sweep 实验摘要" in path.read_text(encoding="utf-8")


def test_metrics_table_csv_saves(tmp_path: Path) -> None:
    path = tmp_path / "metrics_table.csv"

    save_metrics_table_csv([{"variant_name": "v1", "status": "SUCCESS", "buy_count": 1}], path)

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["variant_name"] == "v1"


def _result(tmp_path: Path) -> SweepResult:
    now = datetime.now()
    config_dir = tmp_path / "variants" / "v1" / "config"
    output_dir = tmp_path / "variants" / "v1" / "output"
    config_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    return SweepResult(
        sweep_id="sweep_1",
        sweep_name="demo",
        command="run-pipeline",
        generated_at=now,
        base_config_dir="configs/ashare_alpha",
        output_dir=str(tmp_path),
        registry_dir="registry",
        total_variants=1,
        success_count=1,
        partial_count=0,
        failed_count=0,
        runs=[
            SweepRunRecord(
                variant_name="v1",
                status="SUCCESS",
                experiment_id="exp_1",
                config_dir=str(config_dir),
                output_dir=str(output_dir),
                metrics={"buy_count": 1},
                started_at=now,
                finished_at=now,
                duration_seconds=0.1,
            )
        ],
        summary="ok",
    )
