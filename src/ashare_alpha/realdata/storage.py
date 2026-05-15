from __future__ import annotations

import csv
import json
from pathlib import Path

from ashare_alpha.config import load_yaml_config
from ashare_alpha.realdata.models import RealDataOfflineDrillResult, RealDataOfflineDrillSpec
from ashare_alpha.realdata.renderers import render_realdata_offline_drill_report


def load_realdata_offline_drill_spec(path: Path) -> RealDataOfflineDrillSpec:
    return RealDataOfflineDrillSpec.model_validate(load_yaml_config(path))


def save_realdata_offline_drill_result(result: RealDataOfflineDrillResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")


def load_realdata_offline_drill_result(path: Path) -> RealDataOfflineDrillResult:
    return RealDataOfflineDrillResult.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


def save_realdata_offline_drill_artifacts(result: RealDataOfflineDrillResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    save_realdata_offline_drill_result(result, output_dir / "drill_result.json")
    (output_dir / "drill_report.md").write_text(render_realdata_offline_drill_report(result), encoding="utf-8")
    save_realdata_offline_drill_step_summary_csv(result, output_dir / "step_summary.csv")


def save_realdata_offline_drill_step_summary_csv(result: RealDataOfflineDrillResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "step",
                "status",
                "started_at",
                "finished_at",
                "duration_seconds",
                "outputs",
                "summary",
                "error",
            ],
        )
        writer.writeheader()
        for step in result.steps:
            writer.writerow(
                {
                    "step": step.name,
                    "status": step.status,
                    "started_at": step.started_at.isoformat(),
                    "finished_at": step.finished_at.isoformat() if step.finished_at else "",
                    "duration_seconds": "" if step.duration_seconds is None else f"{step.duration_seconds:.6f}",
                    "outputs": "; ".join(step.output_paths),
                    "summary": json.dumps(step.summary, ensure_ascii=False),
                    "error": step.error_message or "",
                }
            )
