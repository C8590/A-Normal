from __future__ import annotations

import json
from pathlib import Path

from scripts import command_matrix


def test_command_matrix_generates_json_and_markdown(tmp_path: Path, monkeypatch, capsys) -> None:
    json_path = tmp_path / "command_matrix.json"
    doc_path = tmp_path / "COMMAND_MATRIX.md"
    monkeypatch.setattr(command_matrix, "JSON_PATH", json_path)
    monkeypatch.setattr(command_matrix, "DOC_PATH", doc_path)

    code = command_matrix.main()
    capsys.readouterr()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = doc_path.read_text(encoding="utf-8")

    assert code == 0
    assert payload["command_count"] == len(command_matrix.COMMAND_MATRIX)
    assert "# Command Matrix" in markdown


def test_command_matrix_contains_key_commands() -> None:
    commands = {row["command"] for row in command_matrix.COMMAND_MATRIX}

    for command in (
        "run-pipeline",
        "run-backtest",
        "run-sweep",
        "run-walkforward",
        "build-dashboard",
        "cache-source-fixture",
        "materialize-cache",
        "build-frontend",
        "serve-frontend",
        "inspect-realism-data",
        "check-trading-calendar",
        "evaluate-research-gates",
    ):
        assert command in commands


def test_command_matrix_docs_exist() -> None:
    assert Path("docs/COMMAND_MATRIX.md").exists()
    text = Path("docs/COMMAND_MATRIX.md").read_text(encoding="utf-8")
    assert "build-dashboard" in text
    assert "cache-source-fixture" in text
    assert "materialize-cache" in text
    assert "build-frontend" in text
    assert "serve-frontend" in text
    assert "run-pipeline" in text
    assert "inspect-realism-data" in text
    assert "check-trading-calendar" in text
    assert "evaluate-research-gates" in text
