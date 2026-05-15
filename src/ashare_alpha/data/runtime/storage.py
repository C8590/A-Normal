from __future__ import annotations

import json
from pathlib import Path

from ashare_alpha.data.runtime.models import MaterializationResult


def save_materialization_result_json(result: MaterializationResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_materialization_result_json(path: Path) -> MaterializationResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return MaterializationResult.model_validate(payload)
