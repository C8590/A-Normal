from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.data import DataValidationReport
from ashare_alpha.importing import (
    ImportedFile,
    ImportManifest,
    compute_file_sha256,
    load_import_manifest,
    save_import_manifest,
    save_validation_report,
)


def test_compute_file_sha256_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")

    assert compute_file_sha256(path) == compute_file_sha256(path)


def test_save_and_load_import_manifest(tmp_path: Path) -> None:
    path = tmp_path / "import_manifest.json"
    manifest = _manifest()

    save_import_manifest(manifest, path)

    assert load_import_manifest(path) == manifest


def test_save_validation_report(tmp_path: Path) -> None:
    path = tmp_path / "validation_report.json"
    report = DataValidationReport(passed=True, errors=[], warnings=[], row_counts={"daily_bar": 1})

    save_validation_report(report, path)

    assert path.exists()
    assert "daily_bar" in path.read_text(encoding="utf-8")


def _manifest() -> ImportManifest:
    return ImportManifest(
        import_id="local_csv_sample_v1_12345678",
        source_name="local_csv",
        data_version="sample_v1",
        created_at=datetime(2026, 3, 20, 16, 0),
        source_data_dir="source",
        target_data_dir="target",
        config_dir="configs/ashare_alpha",
        copied_files=[
            ImportedFile(
                dataset_name="stock_master",
                source_path="source/stock_master.csv",
                target_path="target/stock_master.csv",
                rows=1,
                sha256="abc",
                copied=True,
            )
        ],
        row_counts={"stock_master": 1},
        validation_passed=True,
        validation_error_count=0,
        validation_warning_count=0,
        snapshot_id="snapshot",
        snapshot_path="target/data_snapshot.json",
        status="SUCCESS",
        error_message=None,
        notes=None,
    )

