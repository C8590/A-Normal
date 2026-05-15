from __future__ import annotations

import json
import subprocess
import sys


def test_inspect_realism_data_cli_runs() -> None:
    result = _run(["inspect-realism-data"])

    assert result.returncode == 0
    assert "trade_calendar" in result.stdout


def test_inspect_realism_data_cli_json_runs() -> None:
    result = _run(["inspect-realism-data", "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["rows"]["trade_calendar"] == 90


def test_check_trading_calendar_cli_runs() -> None:
    result = _run(["check-trading-calendar", "--start", "2026-01-01", "--end", "2026-03-31"])

    assert result.returncode == 0
    assert "Open dates:" in result.stdout


def test_check_trading_calendar_cli_json_runs() -> None:
    result = _run(["check-trading-calendar", "--start", "2026-01-01", "--end", "2026-03-31", "--format", "json"])

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["open_dates_count"] == 63


def test_no_forbidden_realism_imports_or_live_trading_hooks() -> None:
    forbidden = ("import requests", "import httpx", "import tushare", "import akshare", "submit_order")
    for path in __import__("pathlib").Path("src/ashare_alpha").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(item in text for item in forbidden), path
        assert "import a_normal" not in text


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ashare_alpha", *args],
        check=False,
        capture_output=True,
        text=True,
    )
