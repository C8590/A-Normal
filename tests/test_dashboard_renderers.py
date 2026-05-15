from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.dashboard import DashboardScanner, build_dashboard_summary, dashboard_to_json_dict, render_dashboard_markdown
from dashboard_helpers import write_dashboard_fixture


def test_dashboard_markdown_nonempty_and_contains_sections(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    index = DashboardScanner(paths["outputs"]).scan()
    summary = build_dashboard_summary(index)

    markdown = render_dashboard_markdown(index, summary)

    assert "# 研究 Dashboard" in markdown
    assert "不构成投资建议" in markdown
    assert len(markdown) > 100


def test_dashboard_json_dict_serializable(tmp_path: Path) -> None:
    paths = write_dashboard_fixture(tmp_path)
    index = DashboardScanner(paths["outputs"]).scan()
    summary = build_dashboard_summary(index)

    payload = dashboard_to_json_dict(index, summary)

    assert json.dumps(payload, ensure_ascii=False)
