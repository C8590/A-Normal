from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ashare_alpha.dashboard.models import DashboardIndex, DashboardSummary
from ashare_alpha.dashboard.renderers import render_dashboard_markdown


def save_dashboard_index_json(index: DashboardIndex, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_dashboard_index_json(path: Path) -> DashboardIndex:
    return DashboardIndex.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_dashboard_summary_json(summary: DashboardSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_dashboard_summary_json(path: Path) -> DashboardSummary:
    return DashboardSummary.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_dashboard_markdown(index: DashboardIndex, summary: DashboardSummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_dashboard_markdown(index, summary), encoding="utf-8")


def save_dashboard_tables(index: DashboardIndex, summary: DashboardSummary, tables_dir: Path) -> None:
    tables_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(
        tables_dir / "artifacts.csv",
        [
            {
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type,
                "name": artifact.name,
                "created_at": artifact.created_at.isoformat() if artifact.created_at else "",
                "status": artifact.status or "",
                "path": artifact.path,
                "summary": _cell(artifact.summary),
                "related_paths": _cell(artifact.related_paths),
            }
            for artifact in index.artifacts
        ],
    )
    _write_csv(tables_dir / "recent_experiments.csv", summary.recent_experiments)
    _write_csv(tables_dir / "top_candidates.csv", summary.top_candidates)
    _write_csv(tables_dir / "warning_items.csv", summary.warning_items)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    if not fieldnames:
        fieldnames = ["message"]
        rows = [{"message": ""}]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(row.get(key)) for key in fieldnames})


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)
