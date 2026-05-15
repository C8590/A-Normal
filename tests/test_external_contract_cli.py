from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


TUSHARE_FIXTURE = "tests/fixtures/external_sources/tushare_like"
AKSHARE_FIXTURE = "tests/fixtures/external_sources/akshare_like"


def test_validate_adapter_contract_tushare_like_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "validate-adapter-contract",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            TUSHARE_FIXTURE,
            "--output-dir",
            str(tmp_path / "contract"),
        ]
    )

    assert result.returncode == 0
    assert "Adapter contract validation completed" in result.stdout


def test_validate_adapter_contract_akshare_like_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "validate-adapter-contract",
            "--source-name",
            "akshare_like",
            "--fixture-dir",
            AKSHARE_FIXTURE,
            "--output-dir",
            str(tmp_path / "contract"),
        ]
    )

    assert result.returncode == 0


def test_validate_adapter_contract_json_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "validate-adapter-contract",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            TUSHARE_FIXTURE,
            "--output-dir",
            str(tmp_path / "contract"),
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["passed"] is True


def test_validate_adapter_contract_missing_fixture_fails(tmp_path: Path) -> None:
    result = _run(
        [
            "validate-adapter-contract",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            str(tmp_path / "missing"),
            "--output-dir",
            str(tmp_path / "contract"),
        ]
    )

    assert result.returncode != 0


def test_convert_source_fixture_tushare_like_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "convert-source-fixture",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            TUSHARE_FIXTURE,
            "--output-dir",
            str(tmp_path / "converted"),
        ]
    )

    assert result.returncode == 0
    assert (tmp_path / "converted" / "stock_master.csv").exists()


def test_convert_source_fixture_akshare_like_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "convert-source-fixture",
            "--source-name",
            "akshare_like",
            "--fixture-dir",
            AKSHARE_FIXTURE,
            "--output-dir",
            str(tmp_path / "converted"),
        ]
    )

    assert result.returncode == 0
    assert (tmp_path / "converted" / "daily_bar.csv").exists()


def test_convert_source_fixture_json_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "convert-source-fixture",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            TUSHARE_FIXTURE,
            "--output-dir",
            str(tmp_path / "converted"),
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["validation_passed"] is True


def test_converted_output_dir_can_be_used_by_validate_data(tmp_path: Path) -> None:
    converted_dir = _convert(tmp_path)

    assert _run(["validate-data", "--data-dir", str(converted_dir)]).returncode == 0


def test_converted_output_dir_can_be_used_by_quality_report(tmp_path: Path) -> None:
    converted_dir = _convert(tmp_path)

    assert _run(["quality-report", "--data-dir", str(converted_dir), "--output-dir", str(tmp_path / "quality")]).returncode == 0


def test_converted_output_dir_can_be_used_by_import_data(tmp_path: Path) -> None:
    target_root = tmp_path / "imports"
    converted_dir = target_root / "tushare_like" / "contract_sample"
    result = _run(
        [
            "convert-source-fixture",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            TUSHARE_FIXTURE,
            "--output-dir",
            str(converted_dir),
        ]
    )
    assert result.returncode == 0

    import_result = _run(
        [
            "import-data",
            "--source-name",
            "tushare_like",
            "--source-data-dir",
            str(converted_dir),
            "--target-root-dir",
            str(target_root),
            "--data-version",
            "contract_sample",
            "--overwrite",
        ]
    )

    assert import_result.returncode == 0
    assert (converted_dir / "import_manifest.json").exists()


def test_existing_validate_data_command_still_runs() -> None:
    assert _run(["validate-data"]).returncode == 0


def _convert(tmp_path: Path) -> Path:
    output_dir = tmp_path / "converted"
    result = _run(
        [
            "convert-source-fixture",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            TUSHARE_FIXTURE,
            "--output-dir",
            str(output_dir),
        ]
    )
    assert result.returncode == 0
    return output_dir


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
