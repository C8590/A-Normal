from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from ashare_alpha import cli


def test_run_walkforward_runs(tmp_path: Path, capsys) -> None:
    spec_path = _walkforward_spec(tmp_path)

    code = cli.main(["run-walkforward", "--spec", str(spec_path)])
    output = capsys.readouterr().out

    assert code == 0
    assert "Walk-forward run: cli_wf" in output


def test_run_walkforward_json_and_show_run(tmp_path: Path, capsys) -> None:
    spec_path = _walkforward_spec(tmp_path)

    code = cli.main(["run-walkforward", "--spec", str(spec_path), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    result_path = Path(payload["output_dir"]) / "walkforward_result.json"
    assert result_path.exists()

    show_code = cli.main(["show-walkforward", "--path", str(result_path)])
    show_output = capsys.readouterr().out
    show_json_code = cli.main(["show-walkforward", "--path", str(result_path), "--format", "json"])
    show_json = json.loads(capsys.readouterr().out)

    assert show_code == 0
    assert "Walk-forward: cli_wf" in show_output
    assert show_json_code == 0
    assert show_json["name"] == "cli_wf"


def test_run_walkforward_requires_spec() -> None:
    with pytest.raises(SystemExit):
        cli.main(["run-walkforward"])


def test_existing_key_commands_still_run_after_walkforward(tmp_path: Path, capsys) -> None:
    spec_path = _walkforward_spec(tmp_path)
    assert cli.main(["run-walkforward", "--spec", str(spec_path), "--format", "json"]) == 0
    capsys.readouterr()

    commands = [
        ["validate-data"],
        ["show-config"],
        ["run-backtest", "--start", "2026-01-05", "--end", "2026-03-20", "--format", "json"],
        ["run-sweep", "--spec", "configs/ashare_alpha/sweeps/sample_backtest_positions.yaml", "--format", "json"],
    ]
    for command in commands:
        assert cli.main(command) == 0
        capsys.readouterr()


def test_ashare_alpha_has_no_forbidden_imports_or_order_calls() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/ashare_alpha").rglob("*.py"))

    for forbidden in ("import requests", "import httpx", "import tushare", "import akshare", "from a_normal"):
        assert forbidden not in text
    for forbidden_text in ("def submit_order", "def place_order", ".submit_order(", ".place_order("):
        assert forbidden_text not in text


def _walkforward_spec(tmp_path: Path) -> Path:
    payload: dict[str, object] = {
        "name": "cli_wf",
        "command": "run-backtest",
        "data_dir": "data/sample/ashare_alpha",
        "base_config_dir": "configs/ashare_alpha",
        "output_root_dir": str(tmp_path / "walkforward"),
        "experiment_registry_dir": str(tmp_path / "experiments"),
        "start_date": "2026-01-05",
        "end_date": "2026-02-20",
        "train_window_days": None,
        "test_window_days": 14,
        "step_days": 14,
        "min_test_trading_days": 5,
        "common_args": {},
    }
    path = tmp_path / "walkforward.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
