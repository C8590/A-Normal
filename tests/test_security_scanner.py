from __future__ import annotations

from pathlib import Path

import yaml

from ashare_alpha.security import ConfigSecurityScanner


def test_default_config_scans_without_errors() -> None:
    report = ConfigSecurityScanner(Path("configs/ashare_alpha")).scan()

    assert report.passed is True
    assert report.error_count == 0


def test_plaintext_api_key_produces_error(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    _write_yaml(config_dir / "bad.yaml", {"api_key": "plain-secret-value-123"})

    report = ConfigSecurityScanner(config_dir).scan()

    assert report.passed is False
    assert any(issue.issue_type == "plaintext_secret" for issue in report.issues)


def test_env_var_secret_reference_does_not_produce_error(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    _write_yaml(config_dir / "ok.yaml", {"api_key": "ASHARE_ALPHA_VENDOR_TOKEN"})

    report = ConfigSecurityScanner(config_dir).scan()

    assert report.error_count == 0


def test_allow_live_trading_true_produces_error(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    _write_yaml(config_dir / "bad.yaml", {"allow_live_trading": True})

    report = ConfigSecurityScanner(config_dir).scan()

    assert any(issue.issue_type == "live_trading_enabled" for issue in report.issues)


def test_scanner_skips_outputs_data_and_git(tmp_path: Path) -> None:
    for dirname in ("outputs", "data", ".git"):
        skipped = tmp_path / dirname
        skipped.mkdir()
        _write_yaml(skipped / "bad.yaml", {"api_key": "plain-secret-value-123"})

    report = ConfigSecurityScanner(tmp_path).scan()

    assert report.error_count == 0


def _write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
