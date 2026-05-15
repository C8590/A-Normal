from __future__ import annotations

import csv
import shutil
from datetime import date
from pathlib import Path

from ashare_alpha.pipeline import PipelineRunner


SAMPLE_DATE = date(2026, 3, 20)
DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_run_pipeline_default_does_not_execute_quality(tmp_path: Path) -> None:
    manifest = _runner(tmp_path).run()

    assert "quality_report" not in [step.name for step in manifest.steps]


def test_run_pipeline_with_quality_executes_step(tmp_path: Path) -> None:
    manifest = _runner(tmp_path, quality_report=True).run()

    assert manifest.status == "SUCCESS"
    assert _step(manifest, "quality_report").status == "SUCCESS"
    assert (tmp_path / "pipeline" / "quality" / "quality_report.json").exists()


def test_run_pipeline_quality_error_fails_pipeline(tmp_path: Path) -> None:
    data_dir = _copy_sample(tmp_path / "data")
    _rewrite_first_row(data_dir / "daily_bar.csv", {"limit_up": "8", "limit_down": "9"})
    manifest = _runner(tmp_path, data_dir=data_dir, quality_report=True).run()

    assert manifest.status == "FAILED"
    assert _step(manifest, "quality_report").status == "FAILED"


def test_run_pipeline_quality_warning_info_continues(tmp_path: Path) -> None:
    manifest = _runner(tmp_path, quality_report=True).run()

    assert manifest.status == "SUCCESS"
    assert manifest.daily_report_path is not None


def _runner(tmp_path: Path, data_dir: Path = DATA_DIR, quality_report: bool = False) -> PipelineRunner:
    return PipelineRunner(
        date=SAMPLE_DATE,
        data_dir=data_dir,
        config_dir=CONFIG_DIR,
        output_dir=tmp_path / "pipeline",
        quality_report=quality_report,
    )


def _copy_sample(target_dir: Path) -> Path:
    shutil.copytree(DATA_DIR, target_dir)
    return target_dir


def _rewrite_first_row(path: Path, updates: dict[str, str]) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fieldnames = rows[0].keys()
    rows[0].update(updates)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _step(manifest, name: str):
    return next(step for step in manifest.steps if step.name == name)

