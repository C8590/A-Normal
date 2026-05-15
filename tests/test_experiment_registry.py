from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ashare_alpha.experiments import ExperimentRecord, ExperimentRegistry


def test_registry_add_then_get(tmp_path: Path) -> None:
    registry = ExperimentRegistry(tmp_path)
    record = _record("exp_20260101_000000_aaaaaaaa")

    registry.add(record)

    assert registry.get(record.experiment_id).experiment_id == record.experiment_id


def test_registry_list_sorts_descending(tmp_path: Path) -> None:
    registry = ExperimentRegistry(tmp_path)
    old = _record("exp_20260101_000000_aaaaaaaa", created_at=datetime(2026, 1, 1))
    new = _record("exp_20260102_000000_bbbbbbbb", created_at=datetime(2026, 1, 1) + timedelta(days=1))
    registry.add(old)
    registry.add(new)

    assert registry.list()[0].experiment_id == new.experiment_id


def test_registry_find_by_tag_and_command(tmp_path: Path) -> None:
    registry = ExperimentRegistry(tmp_path)
    record = _record("exp_20260101_000000_aaaaaaaa", tags=["mvp"], command="run-pipeline")
    registry.add(record)

    assert registry.find_by_tag("mvp") == [record]
    assert registry.find_by_command("run-pipeline") == [record]


def test_registry_rebuild_index(tmp_path: Path) -> None:
    registry = ExperimentRegistry(tmp_path)
    registry.add(_record("exp_20260101_000000_aaaaaaaa"))

    index = registry.rebuild_index()

    assert len(index.experiments) == 1
    assert (tmp_path / "index.json").exists()


def test_registry_get_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not exist"):
        ExperimentRegistry(tmp_path).get("exp_missing")


def _record(
    experiment_id: str,
    created_at: datetime | None = None,
    tags: list[str] | None = None,
    command: str = "run-backtest",
) -> ExperimentRecord:
    return ExperimentRecord(
        experiment_id=experiment_id,
        created_at=created_at or datetime(2026, 1, 1),
        command=command,
        command_args={},
        status="SUCCESS",
        tags=tags or [],
    )
