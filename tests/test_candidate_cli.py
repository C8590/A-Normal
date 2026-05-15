from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha import cli

from candidate_helpers import write_candidate_rules, write_sweep_source, write_wf_source


def test_select_candidates_walkforward_source_runs(tmp_path: Path, capsys) -> None:
    source = write_wf_source(tmp_path, "wf_cli", 0.2, 0.0, 1.0, 0.0, 3, 1)

    code = cli.main(["select-candidates", "--source", str(source), "--rules", str(write_candidate_rules(tmp_path))])
    output = capsys.readouterr().out

    assert code == 0
    assert "Candidate selection completed" in output


def test_select_candidates_sweep_source_runs(tmp_path: Path, capsys) -> None:
    source = write_sweep_source(tmp_path)

    code = cli.main(["select-candidates", "--source", str(source), "--rules", str(write_candidate_rules(tmp_path))])
    output = capsys.readouterr().out

    assert code == 0
    assert "Total candidates: 2" in output


def test_select_candidates_json_runs(tmp_path: Path, capsys) -> None:
    source = write_wf_source(tmp_path, "wf_cli_json", 0.2, 0.0, 1.0, 0.0, 3, 1)

    code = cli.main(
        ["select-candidates", "--source", str(source), "--rules", str(write_candidate_rules(tmp_path)), "--format", "json"]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["total_candidates"] == 1


def test_select_candidates_missing_source_fails(tmp_path: Path, capsys) -> None:
    code = cli.main(["select-candidates", "--source", str(tmp_path / "missing.json"), "--rules", str(write_candidate_rules(tmp_path))])

    assert code == 1
    assert "does not exist" in capsys.readouterr().err


def test_promote_candidate_config_cli_runs(tmp_path: Path, capsys) -> None:
    source = write_sweep_source(tmp_path)
    config_dir = tmp_path / "review_config"
    config_dir.mkdir()
    (config_dir / "scoring.yaml").write_text("thresholds:\n  buy: 80\n", encoding="utf-8")
    output_dir = tmp_path / "selection"
    assert cli.main(
        [
            "select-candidates",
            "--source",
            str(source),
            "--rules",
            str(write_candidate_rules(tmp_path)),
            "--output-dir",
            str(output_dir),
        ]
    ) == 0
    capsys.readouterr()
    selection = output_dir / "candidate_selection.json"
    candidate_id = json.loads(selection.read_text(encoding="utf-8"))["candidates"][0]["candidate_id"]

    code = cli.main(
        [
            "promote-candidate-config",
            "--selection",
            str(selection),
            "--candidate-id",
            candidate_id,
            "--promoted-name",
            "test_candidate",
            "--target-root",
            str(tmp_path / "candidate_configs"),
        ]
    )
    output = capsys.readouterr().out

    assert code == 0
    assert "Status: SUCCESS" in output


def test_promote_candidate_config_without_config_dir_fails(tmp_path: Path, capsys) -> None:
    source = write_wf_source(tmp_path, "wf_no_config", 0.2, 0.0, 1.0, 0.0, 3, 1)
    output_dir = tmp_path / "selection"
    assert cli.main(
        [
            "select-candidates",
            "--source",
            str(source),
            "--rules",
            str(write_candidate_rules(tmp_path)),
            "--output-dir",
            str(output_dir),
        ]
    ) == 0
    capsys.readouterr()
    selection = output_dir / "candidate_selection.json"
    candidate_id = json.loads(selection.read_text(encoding="utf-8"))["candidates"][0]["candidate_id"]

    code = cli.main(
        [
            "promote-candidate-config",
            "--selection",
            str(selection),
            "--candidate-id",
            candidate_id,
            "--promoted-name",
            "wf_candidate",
        ]
    )

    assert code == 1
    assert "没有 config_dir" in capsys.readouterr().out


def test_existing_key_commands_still_run_after_candidate_selection(tmp_path: Path, capsys) -> None:
    source = write_wf_source(tmp_path, "wf_key", 0.2, 0.0, 1.0, 0.0, 3, 1)
    assert cli.main(["select-candidates", "--source", str(source), "--rules", str(write_candidate_rules(tmp_path))]) == 0
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
