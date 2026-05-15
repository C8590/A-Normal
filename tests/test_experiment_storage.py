from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.experiments import (
    ExperimentIndex,
    ExperimentRecord,
    compare_experiments,
    load_compare_result_json,
    load_experiment_index,
    load_experiment_record,
    save_compare_result_json,
    save_compare_result_md,
    save_experiment_index,
    save_experiment_record,
)


def test_experiment_record_storage_roundtrip(tmp_path: Path) -> None:
    record = _record("exp_20260101_000000_aaaaaaaa")
    path = tmp_path / "record.json"

    save_experiment_record(record, path)

    assert load_experiment_record(path) == record


def test_experiment_index_storage_roundtrip(tmp_path: Path) -> None:
    index = ExperimentIndex(registry_dir=str(tmp_path), generated_at=datetime(2026, 1, 1), experiments=[_record("exp_20260101_000000_aaaaaaaa")])
    path = tmp_path / "index.json"

    save_experiment_index(index, path)

    assert load_experiment_index(path) == index


def test_compare_result_storage_outputs_json_and_md(tmp_path: Path) -> None:
    result = compare_experiments(_record("exp_20260101_000000_aaaaaaaa"), _record("exp_20260101_000001_bbbbbbbb"))
    json_path = tmp_path / "compare.json"
    md_path = tmp_path / "compare.md"

    save_compare_result_json(result, json_path)
    save_compare_result_md(result, md_path)

    assert load_compare_result_json(json_path).baseline_experiment_id == result.baseline_experiment_id
    assert "不构成投资建议" in md_path.read_text(encoding="utf-8")


def _record(experiment_id: str) -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id=experiment_id,
        created_at=datetime(2026, 1, 1),
        command="run-pipeline",
        command_args={},
        status="SUCCESS",
    )
