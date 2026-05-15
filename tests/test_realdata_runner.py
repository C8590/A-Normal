from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.pipeline.storage import load_pipeline_manifest
from ashare_alpha.realdata import RealDataOfflineDrillRunner


def test_tushare_like_offline_drill_runs(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, "tushare")
    result = RealDataOfflineDrillRunner(spec_path).run()

    assert result.status == "SUCCESS"
    assert result.materialized_data_dir is not None
    assert result.imported_data_dir is not None
    assert result.pipeline_output_dir is not None
    assert result.frontend_output_dir is not None
    assert result.dashboard_output_dir is not None
    assert result.experiment_id is not None
    assert (Path(result.output_dir) / "drill_result.json").exists()
    assert (Path(result.output_dir) / "drill_report.md").exists()
    assert (Path(result.output_dir) / "step_summary.csv").exists()
    assert {step.name for step in result.steps} >= {
        "cache_source_fixture",
        "materialize_cache",
        "materialize_source",
        "import_data",
        "validate_data",
        "quality_report",
        "audit_leakage",
        "check_security",
        "run_pipeline",
        "build_frontend",
        "build_dashboard",
        "record_experiment",
    }

    validation = LocalCsvAdapter(Path(result.materialized_data_dir)).validate_all()
    assert validation.passed is True
    pipeline = load_pipeline_manifest(Path(result.pipeline_output_dir) / "manifest.json")
    assert pipeline.status == "SUCCESS"


def test_akshare_like_offline_drill_runs(tmp_path: Path) -> None:
    spec_path = _write_spec(tmp_path, "akshare")
    result = RealDataOfflineDrillRunner(spec_path).run()

    assert result.status == "SUCCESS"
    assert result.source_name == "akshare_like_offline"
    assert result.imported_data_dir is not None
    assert (Path(result.dashboard_output_dir or "") / "dashboard_index.json").exists()


def test_required_step_failure_marks_drill_failed(tmp_path: Path) -> None:
    profile_path = tmp_path / "missing_fixture_profile.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "source_name": "missing_fixture_offline",
                "display_name": "Missing Fixture Offline",
                "mode": "offline_replay",
                "contract_source_name": "tushare_like",
                "mapping_path": "configs/ashare_alpha/data_sources/tushare_like_mapping.yaml",
                "fixture_dir": str(tmp_path / "does_not_exist"),
                "cache_dir": None,
                "output_root_dir": str(tmp_path / "materialized"),
                "data_version_prefix": "missing_fixture",
                "requires_network": False,
                "requires_api_key": False,
                "api_key_env_var": None,
                "enabled": True,
                "notes": "offline test",
            }
        ),
        encoding="utf-8",
    )
    spec_path = _write_spec(tmp_path, "missing", source_profile=profile_path)

    result = RealDataOfflineDrillRunner(spec_path).run()

    assert result.status == "FAILED"
    assert result.steps[0].name == "cache_source_fixture"
    assert result.steps[0].status == "FAILED"


def test_optional_step_failure_marks_drill_partial(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec_path = _write_spec(
        tmp_path,
        "tushare_partial",
        overrides={
            "run_leakage_audit": False,
            "run_security_check": False,
            "run_pipeline": False,
            "build_frontend": False,
            "build_dashboard": False,
            "record_experiment": False,
        },
    )
    runner = RealDataOfflineDrillRunner(spec_path)

    def fail_quality() -> tuple[list[Path], dict[str, object]]:
        raise RuntimeError("forced optional failure")

    monkeypatch.setattr(runner, "_quality_report", fail_quality)

    result = runner.run()

    assert result.status == "PARTIAL"
    assert [step.status for step in result.steps if step.name == "quality_report"] == ["FAILED"]


def test_no_forbidden_network_vendor_or_live_trading_imports() -> None:
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/ashare_alpha").rglob("*.py"))

    for forbidden in ["import requests", "import httpx", "import tushare", "import akshare", "from a_normal"]:
        assert forbidden not in source_text
    realdata_text = "\n".join(path.read_text(encoding="utf-8") for path in Path("src/ashare_alpha/realdata").rglob("*.py"))
    for forbidden in ["urlopen", "socket.", "place_order", "send_order", "broker_submit", "real_order"]:
        assert forbidden not in realdata_text


def _write_spec(
    tmp_path: Path,
    name: str,
    source_profile: Path | None = None,
    overrides: dict[str, object] | None = None,
) -> Path:
    is_akshare = name.startswith("akshare")
    payload: dict[str, object] = {
        "drill_name": f"{name}_offline_drill",
        "source_profile": str(
            source_profile
            or Path(
                "configs/ashare_alpha/source_profiles/"
                f"{'akshare_like_offline' if is_akshare else 'tushare_like_offline'}.yaml"
            )
        ),
        "source_name": "akshare_like_offline" if is_akshare else "tushare_like_offline",
        "data_version": f"pt_{name[:10]}_v0_3",
        "target_date": "2026-03-20",
        "output_root_dir": str(tmp_path / "realdata"),
        "experiment_registry_dir": str(tmp_path / "experiments"),
        "run_quality_report": True,
        "run_leakage_audit": True,
        "run_security_check": True,
        "run_pipeline": True,
        "build_frontend": True,
        "build_dashboard": True,
        "record_experiment": True,
        "notes": "pytest offline drill",
    }
    if source_profile is not None:
        payload["source_name"] = "missing_fixture_offline"
        payload["data_version"] = "pytest_missing_fixture_v0_3"
    if overrides:
        payload.update(overrides)
    spec_path = tmp_path / f"{name}_drill.yaml"
    spec_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return spec_path
