from __future__ import annotations

from datetime import datetime

from ashare_alpha.sweeps.metrics_table import build_metrics_table
from ashare_alpha.sweeps.models import SweepResult, SweepRunRecord


def test_build_metrics_table_includes_pipeline_metrics() -> None:
    now = datetime.now()
    result = SweepResult(
        sweep_id="sweep_1",
        sweep_name="demo",
        command="run-pipeline",
        generated_at=now,
        base_config_dir="configs/ashare_alpha",
        output_dir="out",
        registry_dir="registry",
        total_variants=1,
        success_count=1,
        partial_count=0,
        failed_count=0,
        runs=[
            SweepRunRecord(
                variant_name="buy_80",
                status="SUCCESS",
                experiment_id="exp_1",
                config_dir="config",
                output_dir="output",
                metrics={"buy_count": 1, "watch_count": 2, "block_count": 3},
                started_at=now,
                duration_seconds=0.2,
            )
        ],
        summary="ok",
    )

    rows = build_metrics_table(result)

    assert rows[0]["buy_count"] == 1
    assert rows[0]["watch_count"] == 2
    assert rows[0]["block_count"] == 3
