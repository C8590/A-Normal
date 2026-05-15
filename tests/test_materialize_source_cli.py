from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_materialize_source_tushare_like_runs(tmp_path: Path) -> None:
    result = _materialize("tushare_like_offline", tmp_path, "contract_sample")

    assert result.returncode == 0
    assert (tmp_path / "tushare_like_offline" / "contract_sample" / "stock_master.csv").exists()


def test_materialize_source_akshare_like_runs(tmp_path: Path) -> None:
    result = _materialize("akshare_like_offline", tmp_path, "contract_sample")

    assert result.returncode == 0
    assert (tmp_path / "akshare_like_offline" / "contract_sample" / "daily_bar.csv").exists()


def test_materialize_source_quality_report_runs(tmp_path: Path) -> None:
    result = _materialize("tushare_like_offline", tmp_path, "quality_sample", quality=True)

    assert result.returncode == 0
    assert (tmp_path / "tushare_like_offline" / "quality_sample" / "quality_report.json").exists()


def test_materialize_source_json_runs(tmp_path: Path) -> None:
    result = _run(
        [
            "materialize-source",
            "--profile",
            "configs/ashare_alpha/source_profiles/tushare_like_offline.yaml",
            "--output-root-dir",
            str(tmp_path),
            "--data-version",
            "json_sample",
            "--format",
            "json",
        ]
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["status"] == "SUCCESS"


def test_materialized_output_can_validate_import_and_run_pipeline(tmp_path: Path) -> None:
    materialize_result = _materialize("tushare_like_offline", tmp_path / "materialized", "contract_sample")
    data_dir = tmp_path / "materialized" / "tushare_like_offline" / "contract_sample"

    assert materialize_result.returncode == 0
    assert _run(["validate-data", "--data-dir", str(data_dir)]).returncode == 0
    import_result = _run(
        [
            "import-data",
            "--source-name",
            "tushare_like_offline",
            "--source-data-dir",
            str(data_dir),
            "--target-root-dir",
            str(tmp_path / "imports"),
            "--data-version",
            "contract_sample",
            "--overwrite",
            "--quality-report",
        ]
    )
    assert import_result.returncode == 0
    pipeline_result = _run(
        [
            "run-pipeline",
            "--date",
            "2026-03-20",
            "--data-dir",
            str(tmp_path / "imports" / "tushare_like_offline" / "contract_sample"),
            "--audit-leakage",
            "--quality-report",
            "--check-security",
            "--output-dir",
            str(tmp_path / "pipeline"),
        ]
    )
    assert pipeline_result.returncode == 0


def test_no_forbidden_external_imports_or_live_order_code() -> None:
    forbidden_imports = ("import requests", "import httpx", "import tushare", "import akshare", "from a_normal")
    forbidden_live_calls = ("submit_order", "place_order", "send_order")
    for path in Path("src/ashare_alpha").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(item in text for item in forbidden_imports), path
        assert not any(item in text for item in forbidden_live_calls), path


def _materialize(source_name: str, output_root: Path, data_version: str, quality: bool = False) -> subprocess.CompletedProcess[str]:
    args = [
        "materialize-source",
        "--profile",
        f"configs/ashare_alpha/source_profiles/{source_name}.yaml",
        "--output-root-dir",
        str(output_root),
        "--data-version",
        data_version,
    ]
    if quality:
        args.append("--quality-report")
    return _run(args)


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
