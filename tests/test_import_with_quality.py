from __future__ import annotations

import csv
import shutil
from pathlib import Path

from ashare_alpha.importing import ImportJob


DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_import_data_default_does_not_execute_quality(tmp_path: Path) -> None:
    manifest = _job(tmp_path).run()
    target_dir = tmp_path / "imports" / "local_csv" / "sample_v1"

    assert manifest.status == "SUCCESS"
    assert not (target_dir / "quality_report.json").exists()


def test_import_data_with_quality_writes_files(tmp_path: Path) -> None:
    manifest = _job(tmp_path, quality_report=True).run()
    target_dir = tmp_path / "imports" / "local_csv" / "sample_v1"

    assert manifest.status == "SUCCESS"
    assert (target_dir / "quality_report.json").exists()
    assert (target_dir / "quality_report.md").exists()
    assert (target_dir / "quality_issues.csv").exists()


def test_import_data_quality_error_adds_manifest_note(tmp_path: Path) -> None:
    source_dir = _copy_sample(tmp_path / "source")
    _rewrite_first_row(source_dir / "daily_bar.csv", {"limit_up": "8", "limit_down": "9"})
    manifest = ImportJob(
        source_name="local_csv",
        source_data_dir=source_dir,
        target_root_dir=tmp_path / "imports",
        data_version="sample_v1",
        config_dir=CONFIG_DIR,
        quality_report=True,
    ).run()

    assert manifest.status == "SUCCESS"
    assert manifest.notes is not None
    assert "质量报告存在 error" in manifest.notes


def _job(tmp_path: Path, quality_report: bool = False) -> ImportJob:
    return ImportJob(
        source_name="local_csv",
        source_data_dir=DATA_DIR,
        target_root_dir=tmp_path / "imports",
        data_version="sample_v1",
        config_dir=CONFIG_DIR,
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
