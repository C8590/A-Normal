from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from ashare_alpha.config import load_project_config
from ashare_alpha.sweeps.config_overlay import apply_config_overrides, copy_config_dir


BASE_CONFIG_DIR = Path("configs/ashare_alpha")


def test_copy_config_dir_does_not_modify_base(tmp_path: Path) -> None:
    target = tmp_path / "config"
    before = (BASE_CONFIG_DIR / "scoring.yaml").read_text(encoding="utf-8")

    copy_config_dir(BASE_CONFIG_DIR, target)

    assert (target / "scoring.yaml").exists()
    assert (BASE_CONFIG_DIR / "scoring.yaml").read_text(encoding="utf-8") == before


def test_apply_config_overrides_changes_threshold(tmp_path: Path) -> None:
    config_dir = _copied_config(tmp_path)

    changes = apply_config_overrides(config_dir, {"scoring.yaml": {"thresholds.buy": 85}})

    assert changes == ["scoring.yaml: thresholds.buy 80 -> 85"]
    payload = yaml.safe_load((config_dir / "scoring.yaml").read_text(encoding="utf-8"))
    assert payload["thresholds"]["buy"] == 85


def test_apply_config_overrides_rejects_missing_dot_path(tmp_path: Path) -> None:
    config_dir = _copied_config(tmp_path)

    with pytest.raises(ValueError, match="dot path"):
        apply_config_overrides(config_dir, {"scoring.yaml": {"thresholds.missing": 85}})


def test_apply_config_overrides_rejects_missing_file(tmp_path: Path) -> None:
    config_dir = _copied_config(tmp_path)

    with pytest.raises(ValueError, match="does not exist"):
        apply_config_overrides(config_dir, {"missing.yaml": {"x.y": 1}})


def test_apply_config_overrides_validates_project_config(tmp_path: Path) -> None:
    config_dir = _copied_config(tmp_path)

    apply_config_overrides(config_dir, {"scoring.yaml": {"thresholds.buy": 90}})

    assert load_project_config(config_dir).scoring.thresholds.buy == 90


def test_apply_config_overrides_rejects_allow_network_true(tmp_path: Path) -> None:
    config_dir = _copied_config(tmp_path)

    with pytest.raises(ValueError, match="allow_network"):
        apply_config_overrides(config_dir, {"security.yaml": {"allow_network": True}})


def test_apply_config_overrides_rejects_offline_mode_false(tmp_path: Path) -> None:
    config_dir = _copied_config(tmp_path)

    with pytest.raises(ValueError, match="offline_mode"):
        apply_config_overrides(config_dir, {"security.yaml": {"offline_mode": False}})


def test_apply_config_overrides_rejects_plaintext_secret(tmp_path: Path) -> None:
    config_dir = _copied_config(tmp_path)

    with pytest.raises(ValueError, match="plaintext secret"):
        apply_config_overrides(
            config_dir,
            {"security.yaml": {"data_sources.local_csv.api_key_env_var": "PLAIN_TOKEN"}},
        )


def _copied_config(tmp_path: Path) -> Path:
    config_dir = tmp_path / "config"
    copy_config_dir(BASE_CONFIG_DIR, config_dir)
    shutil.rmtree(config_dir / "sweeps", ignore_errors=True)
    return config_dir
