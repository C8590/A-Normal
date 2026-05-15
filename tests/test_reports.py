from __future__ import annotations

import json

from a_normal.cli import main
from a_normal.data import LocalCsvAdapter
from a_normal.reports import generate_daily_report, save_daily_report


def test_generate_daily_report_from_sample_data():
    report = generate_daily_report("2026-03-26", adapter=LocalCsvAdapter())

    assert report.report_date.isoformat() == "2026-03-26"
    assert report.market_regime == "normal"
    assert 0 <= report.total_position_advice <= 1
    assert len(report.candidates_top20) <= 20
    assert report.blocked_stocks
    assert report.risk_disclosure == "风险提示：本报告不是投资建议，不保证收益。"
    assert "scoring" in report.config_summary
    assert "trading_rules" in report.config_summary


def test_save_daily_report_outputs_markdown_csv_and_json(tmp_path):
    report = generate_daily_report("2026-03-26", adapter=LocalCsvAdapter())

    paths = save_daily_report(report, tmp_path)

    markdown = paths["markdown"].read_text(encoding="utf-8")
    csv_content = paths["csv"].read_text(encoding="utf-8")
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))

    assert "# 每日报告 2026-03-26" in markdown
    assert "候选股票 Top 20" in markdown
    assert "禁买股票" in markdown
    assert "当前配置摘要" in markdown
    assert "本报告不是投资建议，不保证收益" in markdown
    assert csv_content.splitlines()[0].startswith("section,report_date,market_regime,ts_code")
    assert payload["report_date"] == "2026-03-26"
    assert payload["risk_disclosure"] == "风险提示：本报告不是投资建议，不保证收益。"


def test_cli_report_generates_all_formats(tmp_path, capsys):
    exit_code = main(["report", "--date", "2026-03-26", "--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Markdown:" in captured.out
    assert "CSV:" in captured.out
    assert "JSON:" in captured.out
    assert (tmp_path / "daily_report_2026-03-26.md").exists()
    assert (tmp_path / "daily_report_2026-03-26.csv").exists()
    assert (tmp_path / "daily_report_2026-03-26.json").exists()
