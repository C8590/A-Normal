from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha import cli
from dashboard_helpers import write_dashboard_fixture


def test_build_frontend_cli_runs(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)
    output_dir = tmp_path / "frontend_out"

    code = cli.main(["build-frontend", "--outputs-root", str(paths["outputs"]), "--output-dir", str(output_dir)])
    output = capsys.readouterr().out

    assert code == 0
    assert "Research frontend built" in output
    assert (output_dir / "index.html").exists()


def test_build_frontend_cli_json_runs(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)
    output_dir = tmp_path / "frontend_out"

    code = cli.main(["build-frontend", "--outputs-root", str(paths["outputs"]), "--output-dir", str(output_dir), "--format", "json"])
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["artifact_count"] >= 10
    assert payload["output_dir"] == str(output_dir)


def test_build_frontend_cli_update_latest_runs(tmp_path: Path, capsys) -> None:
    paths = write_dashboard_fixture(tmp_path)
    output_dir = tmp_path / "frontend" / "frontend_20260515_090000"

    code = cli.main(["build-frontend", "--outputs-root", str(paths["outputs"]), "--output-dir", str(output_dir), "--update-latest"])
    capsys.readouterr()

    assert code == 0
    assert (paths["outputs"] / "frontend" / "latest" / "index.html").exists()


def test_serve_frontend_missing_dir_fails(tmp_path: Path, capsys) -> None:
    code = cli.main(["serve-frontend", "--dir", str(tmp_path / "missing_dir")])

    assert code == 1
    assert "frontend directory does not exist" in capsys.readouterr().err


def test_frontend_commands_are_registered() -> None:
    parser = cli.build_parser()
    help_text = parser.format_help()

    assert "build-frontend" in help_text
    assert "serve-frontend" in help_text


def test_ashare_alpha_has_no_forbidden_imports_or_live_trading_calls() -> None:
    text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/ashare_alpha").rglob("*.py"))

    for forbidden in (
        "import a_normal",
        "from a_normal",
        "import requests",
        "from requests",
        "import httpx",
        "from httpx",
        "import tushare",
        "from tushare",
        "import akshare",
        "from akshare",
    ):
        assert forbidden not in text
    for forbidden_text in ("def submit_order", "def place_order", ".submit_order(", ".place_order("):
        assert forbidden_text not in text


def test_frontend_has_no_external_api_cdn_npm_or_broker_actions() -> None:
    text_suffixes = {".py", ".html", ".js", ".css"}
    texts = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/ashare_alpha/frontend").rglob("*")
        if path.is_file() and path.suffix in text_suffixes
    )

    for forbidden in ("fetch(", "XMLHttpRequest", "cdn.", "unpkg.com", "npm ", "submit_order", "place_order", "broker_api"):
        assert forbidden not in texts
