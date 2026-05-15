from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha import cli


def test_cache_source_fixture_cli_runs(tmp_path: Path, capsys) -> None:
    code = cli.main(
        [
            "cache-source-fixture",
            "--source-name",
            "tushare_like",
            "--fixture-dir",
            "tests/fixtures/external_sources/tushare_like",
            "--cache-root",
            str(tmp_path / "cache"),
            "--cache-version",
            "cli_v1",
        ]
    )
    output = capsys.readouterr().out

    assert code == 0
    assert "Source fixture cached" in output


def test_cache_source_fixture_cli_json_runs(tmp_path: Path, capsys) -> None:
    code = cli.main(
        [
            "cache-source-fixture",
            "--source-name",
            "akshare_like",
            "--fixture-dir",
            "tests/fixtures/external_sources/akshare_like",
            "--cache-root",
            str(tmp_path / "cache"),
            "--cache-version",
            "cli_json",
            "--format",
            "json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["status"] == "RAW_CACHED"


def test_list_inspect_and_materialize_cache_cli_run(tmp_path: Path, capsys) -> None:
    cache_root = tmp_path / "cache"
    assert (
        cli.main(
            [
                "cache-source-fixture",
                "--source-name",
                "tushare_like",
                "--fixture-dir",
                "tests/fixtures/external_sources/tushare_like",
                "--cache-root",
                str(cache_root),
                "--cache-version",
                "cli_flow",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert cli.main(["list-caches", "--cache-root", str(cache_root)]) == 0
    assert "tushare_like" in capsys.readouterr().out

    assert (
        cli.main(
            [
                "inspect-cache",
                "--source-name",
                "tushare_like",
                "--cache-version",
                "cli_flow",
                "--cache-root",
                str(cache_root),
            ]
        )
        == 0
    )
    assert "Raw contract passed: True" in capsys.readouterr().out

    assert (
        cli.main(
            [
                "materialize-cache",
                "--source-name",
                "tushare_like",
                "--cache-version",
                "cli_flow",
                "--cache-root",
                str(cache_root),
            ]
        )
        == 0
    )
    assert "Cache materialization completed" in capsys.readouterr().out
    assert (cache_root / "tushare_like" / "cli_flow" / "normalized" / "stock_master.csv").exists()
