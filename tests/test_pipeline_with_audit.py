from __future__ import annotations

from datetime import date
from pathlib import Path

from ashare_alpha.pipeline import PipelineRunner


SAMPLE_DATE = date(2026, 3, 20)
DATA_DIR = Path("data/sample/ashare_alpha")
CONFIG_DIR = Path("configs/ashare_alpha")


def test_run_pipeline_default_does_not_execute_audit(tmp_path: Path) -> None:
    manifest = _runner(tmp_path).run()

    assert "audit_leakage" not in [step.name for step in manifest.steps]


def test_run_pipeline_with_audit_executes_step(tmp_path: Path) -> None:
    manifest = _runner(tmp_path, audit_leakage=True).run()

    assert manifest.status == "SUCCESS"
    assert _step(manifest, "audit_leakage").status == "SUCCESS"
    assert (tmp_path / "pipeline" / "audit" / "audit_report.json").exists()


def test_run_pipeline_audit_error_fails_pipeline(tmp_path: Path) -> None:
    manifest = _runner(tmp_path, audit_leakage=True, audit_source_name="").run()

    assert manifest.status == "FAILED"
    assert _step(manifest, "audit_leakage").status == "FAILED"


def test_run_pipeline_audit_warning_info_continues(tmp_path: Path) -> None:
    manifest = _runner(tmp_path, audit_leakage=True).run()

    assert manifest.status == "SUCCESS"
    assert manifest.daily_report_path is not None


def _runner(
    tmp_path: Path,
    audit_leakage: bool = False,
    audit_source_name: str = "local_csv",
) -> PipelineRunner:
    return PipelineRunner(
        date=SAMPLE_DATE,
        data_dir=DATA_DIR,
        config_dir=CONFIG_DIR,
        output_dir=tmp_path / "pipeline",
        audit_leakage=audit_leakage,
        audit_source_name=audit_source_name,
    )


def _step(manifest, name: str):
    return next(step for step in manifest.steps if step.name == name)

