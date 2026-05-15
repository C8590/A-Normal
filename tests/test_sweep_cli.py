from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ashare_alpha import cli


def test_run_sweep_sample_pipeline_runs(tmp_path: Path, capsys) -> None:
    spec_path = _pipeline_spec(tmp_path)

    code = cli.main(["run-sweep", "--spec", str(spec_path)])
    output = capsys.readouterr().out

    assert code == 0
    assert "Sweep run: cli_pipeline" in output
    assert "Success: 1" in output


def test_run_sweep_json_and_show_sweep_run(tmp_path: Path, capsys) -> None:
    spec_path = _pipeline_spec(tmp_path)

    code = cli.main(["run-sweep", "--spec", str(spec_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    result_path = Path(payload["output_dir"]) / "sweep_result.json"
    assert result_path.exists()

    show_code = cli.main(["show-sweep", "--path", str(result_path)])
    show_output = capsys.readouterr().out
    json_code = cli.main(["show-sweep", "--path", str(result_path), "--format", "json"])
    show_json = json.loads(capsys.readouterr().out)

    assert show_code == 0
    assert "cli_pipeline" in show_output
    assert json_code == 0
    assert show_json["sweep_name"] == "cli_pipeline"


def test_run_sweep_requires_spec() -> None:
    with pytest.raises(SystemExit):
        cli.main(["run-sweep"])


def test_run_sweep_all_failed_returns_nonzero(tmp_path: Path, capsys) -> None:
    spec_path = _write_spec(
        tmp_path,
        {
            "sweep_name": "all_failed",
            "command": "run-pipeline",
            "base_config_dir": "configs/ashare_alpha",
            "data_dir": "data/sample/ashare_alpha",
            "output_root_dir": str(tmp_path / "sweeps"),
            "experiment_registry_dir": str(tmp_path / "experiments"),
            "common_args": {"date": "2026-03-20"},
            "variants": [
                {"name": "bad1", "config_overrides": {"scoring.yaml": {"thresholds.missing1": 80}}},
                {"name": "bad2", "config_overrides": {"scoring.yaml": {"thresholds.missing2": 85}}},
            ],
        },
    )

    code = cli.main(["run-sweep", "--spec", str(spec_path)])

    assert code == 1
    assert "Failed: 2" in capsys.readouterr().out


def test_existing_key_commands_still_run_after_sweep(tmp_path: Path, capsys) -> None:
    spec_path = _pipeline_spec(tmp_path)
    assert cli.main(["run-sweep", "--spec", str(spec_path), "--format", "json"]) == 0
    capsys.readouterr()

    commands = [
        ["validate-data"],
        ["show-config"],
        ["run-pipeline", "--date", "2026-03-20", "--format", "json"],
        ["run-backtest", "--start", "2026-01-05", "--end", "2026-03-20", "--format", "json"],
        ["train-probability-model", "--start", "2026-01-05", "--end", "2026-03-20", "--format", "json"],
    ]
    for command in commands:
        assert cli.main(command) == 0
        capsys.readouterr()


def test_ashare_alpha_has_no_forbidden_imports_or_live_trading_calls() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/ashare_alpha").rglob("*.py"))

    for forbidden in ("import requests", "import httpx", "import tushare", "import akshare", "from a_normal"):
        assert forbidden not in text
    for forbidden_text in ("def submit_order", "def place_order", ".submit_order(", ".place_order("):
        assert forbidden_text not in text


def _pipeline_spec(tmp_path: Path) -> Path:
    return _write_spec(
        tmp_path,
        {
            "sweep_name": "cli_pipeline",
            "command": "run-pipeline",
            "base_config_dir": "configs/ashare_alpha",
            "data_dir": "data/sample/ashare_alpha",
            "output_root_dir": str(tmp_path / "sweeps"),
            "experiment_registry_dir": str(tmp_path / "experiments"),
            "common_args": {"date": "2026-03-20"},
            "variants": [{"name": "buy_85", "config_overrides": {"scoring.yaml": {"thresholds.buy": 85}}}],
        },
    )


def _write_spec(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "sweep.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
