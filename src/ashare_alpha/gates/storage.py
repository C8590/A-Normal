from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ashare_alpha.gates.models import ResearchGateReport
from ashare_alpha.gates.renderers import render_research_gate_report_md


def save_research_gate_report_json(report: ResearchGateReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_research_gate_report_json(path: Path) -> ResearchGateReport:
    return ResearchGateReport.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_research_gate_report_md(report: ResearchGateReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_research_gate_report_md(report), encoding="utf-8")


def save_research_gate_issues_csv(report: ResearchGateReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "severity",
        "gate_name",
        "artifact_type",
        "artifact_path",
        "issue_type",
        "message",
        "recommendation",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for issue in report.issues:
            writer.writerow({key: _cell(issue.model_dump(mode="json").get(key)) for key in fieldnames})


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
