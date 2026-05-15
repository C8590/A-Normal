from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml

from ashare_alpha.experiments import create_experiment_id, hash_config_dir, hash_file


def test_hash_file_is_stable(tmp_path: Path) -> None:
    path = tmp_path / "config.yaml"
    path.write_text("a: 1\n", encoding="utf-8")

    assert hash_file(path) == hash_file(path)


def test_hash_config_dir_same_content_same_hash(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    _write_yaml(left / "a.yaml", {"x": 1})
    _write_yaml(right / "a.yaml", {"x": 1})

    assert hash_config_dir(left) == hash_config_dir(right)


def test_hash_config_dir_changes_when_content_changes(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    path = config_dir / "a.yaml"
    _write_yaml(path, {"x": 1})
    before = hash_config_dir(config_dir)
    _write_yaml(path, {"x": 2})

    assert hash_config_dir(config_dir) != before


def test_create_experiment_id_format() -> None:
    experiment_id = create_experiment_id(
        "run-pipeline",
        {"date": "2026-03-20"},
        "a" * 64,
        "sample",
        datetime(2026, 3, 20, 12, 30, 5),
    )

    assert experiment_id.startswith("exp_20260320_123005_")
    assert len(experiment_id.rsplit("_", 1)[-1]) == 8


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
