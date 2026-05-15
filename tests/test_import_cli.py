from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


DATA_DIR = "data/sample/ashare_alpha"
DATE = "2026-03-20"


def test_import_data_sample_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "import-data",
            "--source-name",
            "local_csv",
            "--source-data-dir",
            DATA_DIR,
            "--target-root-dir",
            str(tmp_path / "imports"),
        ]
    )

    assert result.returncode == 0
    assert "Data import completed" in result.stdout


def test_import_data_json_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "import-data",
            "--source-name",
            "local_csv",
            "--source-data-dir",
            DATA_DIR,
            "--target-root-dir",
            str(tmp_path / "imports"),
            "--data-version",
            "sample_v1",
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "SUCCESS"


def test_import_data_specific_version_writes_directory(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    result = _import_sample(target_root)

    assert result.returncode == 0
    assert (target_root / "local_csv" / "sample_v1").exists()


def test_import_data_repeated_version_without_overwrite_fails(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    assert _import_sample(target_root).returncode == 0

    result = _import_sample(target_root)

    assert result.returncode != 0


def test_import_data_overwrite_runs(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    assert _import_sample(target_root).returncode == 0

    result = _import_sample(target_root, "--overwrite")

    assert result.returncode == 0


def test_list_imports_runs(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    assert _import_sample(target_root).returncode == 0

    result = _run(["list-imports", "--target-root-dir", str(target_root)])

    assert result.returncode == 0
    assert "sample_v1" in result.stdout


def test_list_imports_json_runs(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    assert _import_sample(target_root).returncode == 0

    result = _run(["list-imports", "--target-root-dir", str(target_root), "--format", "json"])

    assert result.returncode == 0
    assert json.loads(result.stdout)[0]["data_version"] == "sample_v1"


def test_inspect_import_runs(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    assert _import_sample(target_root).returncode == 0

    result = _run(
        [
            "inspect-import",
            "--source-name",
            "local_csv",
            "--data-version",
            "sample_v1",
            "--target-root-dir",
            str(target_root),
        ]
    )

    assert result.returncode == 0
    assert "Import: local_csv/sample_v1" in result.stdout


def test_inspect_import_missing_record_fails(tmp_path: Path) -> None:
    result = _run(
        [
            "inspect-import",
            "--source-name",
            "local_csv",
            "--data-version",
            "missing",
            "--target-root-dir",
            str(tmp_path / "imports"),
        ]
    )

    assert result.returncode != 0


def test_imported_data_dir_can_validate_and_run_pipeline(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    assert _import_sample(target_root).returncode == 0
    imported_dir = target_root / "local_csv" / "sample_v1"

    assert _run(["validate-data", "--data-dir", str(imported_dir)]).returncode == 0
    pipeline_dir = tmp_path / "pipeline"
    result = _run(
        [
            "run-pipeline",
            "--date",
            DATE,
            "--data-dir",
            str(imported_dir),
            "--audit-leakage",
            "--output-dir",
            str(pipeline_dir),
        ]
    )

    assert result.returncode == 0
    assert (pipeline_dir / "manifest.json").exists()


def _import_sample(target_root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            "import-data",
            "--source-name",
            "local_csv",
            "--source-data-dir",
            DATA_DIR,
            "--target-root-dir",
            str(target_root),
            "--data-version",
            "sample_v1",
            *extra,
        ]
    )


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )
