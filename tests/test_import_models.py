from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.importing import ImportedFile, ImportManifest


def test_imported_file_validates() -> None:
    item = ImportedFile(
        dataset_name="daily_bar",
        source_path="source/daily_bar.csv",
        target_path="target/daily_bar.csv",
        rows=10,
        sha256="abc",
        copied=True,
    )

    assert item.dataset_name == "daily_bar"


def test_import_manifest_validates() -> None:
    manifest = _manifest()

    assert manifest.status == "SUCCESS"


def test_failed_import_manifest_requires_error_message() -> None:
    with pytest.raises(ValidationError, match="error_message"):
        _manifest(status="FAILED", error_message=None, copied_files=[])


def test_import_manifest_rejects_empty_source_name() -> None:
    with pytest.raises(ValidationError):
        _manifest(source_name="")


def _manifest(**overrides) -> ImportManifest:
    payload = {
        "import_id": "local_csv_sample_v1_12345678",
        "source_name": "local_csv",
        "data_version": "sample_v1",
        "created_at": datetime(2026, 3, 20, 16, 0),
        "source_data_dir": "data/sample/ashare_alpha",
        "target_data_dir": "data/imports/local_csv/sample_v1",
        "config_dir": "configs/ashare_alpha",
        "copied_files": [
            ImportedFile(
                dataset_name="stock_master",
                source_path="source/stock_master.csv",
                target_path="target/stock_master.csv",
                rows=1,
                sha256="abc",
                copied=True,
            )
        ],
        "row_counts": {"stock_master": 1},
        "validation_passed": True,
        "validation_error_count": 0,
        "validation_warning_count": 0,
        "snapshot_id": "snapshot",
        "snapshot_path": "target/data_snapshot.json",
        "status": "SUCCESS",
        "error_message": None,
        "notes": None,
    }
    payload.update(overrides)
    return ImportManifest(**payload)

