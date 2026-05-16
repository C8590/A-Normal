from __future__ import annotations

import csv
import json
from pathlib import Path

from ashare_alpha.adjusted.models import AdjustedBuildSummary, AdjustedDailyBarRecord
from ashare_alpha.adjusted.report import render_adjusted_report_markdown
from ashare_alpha.adjusted.validation import AdjustedValidationReport


def save_adjusted_daily_bar_csv(records: list[AdjustedDailyBarRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(AdjustedDailyBarRecord.model_fields)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            row["quality_flags"] = ";".join(record.quality_flags)
            writer.writerow(row)


def save_adjusted_summary_json(summary: AdjustedBuildSummary, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def save_adjusted_validation_json(report: AdjustedValidationReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def save_adjusted_report_md(
    summary: AdjustedBuildSummary,
    validation_report: AdjustedValidationReport,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_adjusted_report_markdown(summary, validation_report), encoding="utf-8")
