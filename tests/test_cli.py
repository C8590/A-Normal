from __future__ import annotations

from a_normal.cli import main


def test_cli_help_for_required_commands(capsys):
    commands = [
        "validate-data",
        "build-universe",
        "compute-factors",
        "generate-signals",
        "run-backtest",
        "report",
        "run-pipeline",
    ]

    for command in commands:
        try:
            main([command, "--help"])
        except SystemExit as exc:
            assert exc.code == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out


def test_cli_commands_run_with_sample_data(tmp_path, capsys):
    assert main(["validate-data", "--output-dir", str(tmp_path / "validation")]) == 0
    assert main(["build-universe", "--date", "2026-03-26", "--output-dir", str(tmp_path / "universe")]) == 0
    assert main(["compute-factors", "--date", "2026-03-26", "--output-dir", str(tmp_path / "factors")]) == 0
    assert main(["generate-signals", "--date", "2026-03-26", "--output-dir", str(tmp_path / "signals")]) == 0
    assert main(["run-backtest", "--start", "2026-01-02", "--end", "2026-03-26", "--output-dir", str(tmp_path / "backtests")]) == 0
    assert main(["report", "--date", "2026-03-26", "--output-dir", str(tmp_path / "reports")]) == 0
    assert main(["run-pipeline", "--date", "2026-03-26", "--output-dir", str(tmp_path / "pipeline")]) == 0

    assert (tmp_path / "validation" / "validation_summary.json").exists()
    assert (tmp_path / "universe" / "universe_daily_2026-03-26.csv").exists()
    assert (tmp_path / "factors" / "factor_daily_2026-03-26.csv").exists()
    assert (tmp_path / "signals" / "signals_2026-03-26.csv").exists()
    assert (tmp_path / "backtests" / "report.md").exists()
    assert (tmp_path / "reports" / "daily_report_2026-03-26.json").exists()
    assert (tmp_path / "pipeline" / "reports" / "daily_report_2026-03-26.md").exists()
    assert capsys.readouterr().err == ""


def test_cli_invalid_date_has_clear_error(capsys):
    exit_code = main(["compute-factors", "--date", "20260326"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid date" in captured.err
