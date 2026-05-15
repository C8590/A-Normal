from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha import cli
from dashboard_helpers import write_dashboard_fixture


def test_build_dashboard_runs(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)

    code = cli.main(["build-dashboard", "--outputs-root", str(paths["outputs"])])
    output = capsys.readouterr().out

    assert code == 0
    assert "Research dashboard built" in output


def test_build_dashboard_json_runs(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)

    code = cli.main(["build-dashboard", "--outputs-root", str(paths["outputs"]), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["artifact_count"] >= 10


def test_build_dashboard_output_dir_files_exist(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)
    output_dir = tmp_path / "dashboard_out"

    code = cli.main(["build-dashboard", "--outputs-root", str(paths["outputs"]), "--output-dir", str(output_dir)])
    capsys.readouterr()

    assert code == 0
    assert (output_dir / "dashboard_index.json").exists()
    assert (output_dir / "dashboard_summary.json").exists()
    assert (output_dir / "dashboard.md").exists()
    assert (output_dir / "dashboard_tables" / "artifacts.csv").exists()


def test_show_dashboard_directory_and_index_run(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)
    output_dir = tmp_path / "dashboard_out"
    assert cli.main(["build-dashboard", "--outputs-root", str(paths["outputs"]), "--output-dir", str(output_dir)]) == 0
    capsys.readouterr()

    dir_code = cli.main(["show-dashboard", "--path", str(output_dir)])
    dir_output = capsys.readouterr().out
    index_code = cli.main(["show-dashboard", "--path", str(output_dir / "dashboard_index.json")])
    index_output = capsys.readouterr().out

    assert dir_code == 0
    assert index_code == 0
    assert "Research dashboard" in dir_output
    assert "Research dashboard" in index_output


def test_build_dashboard_missing_outputs_root_fails(tmp_path: Path, capsys) -> None:
    code = cli.main(["build-dashboard", "--outputs-root", str(tmp_path / "missing")])

    assert code == 1
    assert "outputs_root does not exist" in capsys.readouterr().err


def test_existing_key_commands_still_run_after_dashboard(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)
    assert cli.main(["build-dashboard", "--outputs-root", str(paths["outputs"])]) == 0
    capsys.readouterr()

    for command in (["validate-data"], ["show-config"]):
        assert cli.main(command) == 0
        capsys.readouterr()


def test_ashare_alpha_has_no_forbidden_imports_or_live_trading_calls() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/ashare_alpha").rglob("*.py"))

    for forbidden in ("import requests", "import httpx", "import tushare", "import akshare", "from a_normal"):
        assert forbidden not in text
    for forbidden_text in ("def submit_order", "def place_order", ".submit_order(", ".place_order("):
        assert forbidden_text not in text
