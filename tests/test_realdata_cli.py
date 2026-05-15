from __future__ import annotations

import json
from pathlib import Path

import yaml

from ashare_alpha import cli


def test_run_realdata_offline_drill_cli_runs(tmp_path: Path, capsys) -> None:
    spec_path = _write_cli_spec(tmp_path)

    code = cli.main(["run-realdata-offline-drill", "--spec", str(spec_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "SUCCESS"
    assert Path(payload["output_dir"], "drill_result.json").exists()


def test_show_realdata_drill_cli_runs(tmp_path: Path, capsys) -> None:
    spec_path = _write_cli_spec(tmp_path)
    assert cli.main(["run-realdata-offline-drill", "--spec", str(spec_path), "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    code = cli.main(["show-realdata-drill", "--path", str(Path(payload["output_dir"]) / "drill_result.json")])
    output = capsys.readouterr().out

    assert code == 0
    assert payload["drill_id"] in output
    assert "Steps:" in output


def _write_cli_spec(tmp_path: Path) -> Path:
    payload = {
        "drill_name": "cli_tushare_offline_drill",
        "source_profile": "configs/ashare_alpha/source_profiles/tushare_like_offline.yaml",
        "source_name": "tushare_like_offline",
        "data_version": "pytest_cli_v0_3",
        "target_date": "2026-03-20",
        "output_root_dir": str(tmp_path / "realdata"),
        "experiment_registry_dir": str(tmp_path / "experiments"),
        "run_quality_report": True,
        "run_leakage_audit": False,
        "run_security_check": False,
        "run_pipeline": True,
        "build_frontend": True,
        "build_dashboard": True,
        "record_experiment": True,
        "notes": "pytest cli offline drill",
    }
    spec_path = tmp_path / "cli_drill.yaml"
    spec_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return spec_path
