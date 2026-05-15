from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from ashare_alpha.audit import (
    LeakageAuditor,
    save_leakage_audit_report_json,
    save_leakage_audit_report_md,
)
from ashare_alpha.config import load_yaml_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.data.cache import ExternalCacheStore
from ashare_alpha.data.runtime import SourceMaterializer, SourceProfile
from ashare_alpha.experiments import ExperimentRecorder, ExperimentRegistry
from ashare_alpha.frontend import collect_frontend_data, save_frontend_site
from ashare_alpha.importing import ImportJob, normalize_source_name
from ashare_alpha.importing.storage import save_validation_report
from ashare_alpha.pipeline import PipelineRunner
from ashare_alpha.quality import (
    DataQualityReporter,
    save_quality_issues_csv,
    save_quality_report_json,
    save_quality_report_md,
)
from ashare_alpha.realdata.models import (
    RealDataOfflineDrillResult,
    RealDataOfflineDrillSpec,
    RealDataOfflineDrillStep,
)
from ashare_alpha.realdata.storage import (
    load_realdata_offline_drill_spec,
    save_realdata_offline_drill_artifacts,
)
from ashare_alpha.security import (
    ConfigSecurityScanner,
    save_security_scan_report_json,
    save_security_scan_report_md,
)
from ashare_alpha.dashboard import (
    DashboardScanner,
    build_dashboard_summary,
    save_dashboard_index_json,
    save_dashboard_markdown,
    save_dashboard_summary_json,
    save_dashboard_tables,
)


RequiredAction = Callable[[], tuple[list[Path], dict[str, Any]]]


class RealDataOfflineDrillRunner:
    def __init__(
        self,
        spec: Path | RealDataOfflineDrillSpec,
        output_dir: Path | None = None,
        config_dir: Path = Path("configs/ashare_alpha"),
    ) -> None:
        self.spec = load_realdata_offline_drill_spec(spec) if isinstance(spec, Path) else spec
        self.config_dir = Path(config_dir)
        self.output_root_dir = Path(output_dir) if output_dir is not None else Path(self.spec.output_root_dir)
        self.drill_id = _new_drill_id(self.spec)
        self.drill_dir = self.output_root_dir / self.drill_id
        self.steps: list[RealDataOfflineDrillStep] = []
        self.summary: dict[str, Any] = {}
        self.profile: SourceProfile | None = None
        self.cache_dir: Path | None = None
        self.materialized_data_dir: Path | None = None
        self.imported_data_dir: Path | None = None
        self.validation_report_path: Path | None = None
        self.quality_report_dir: Path | None = None
        self.leakage_audit_dir: Path | None = None
        self.security_report_dir: Path | None = None
        self.pipeline_output_dir: Path | None = None
        self.frontend_output_dir: Path | None = None
        self.dashboard_output_dir: Path | None = None
        self.experiment_id: str | None = None
        self._required_failed = False
        self._optional_failed = False

    def run(self) -> RealDataOfflineDrillResult:
        self.drill_dir.mkdir(parents=True, exist_ok=True)
        self.profile = self._load_profile()

        for name, action in [
            ("cache_source_fixture", self._cache_source_fixture),
            ("materialize_cache", self._materialize_cache),
            ("materialize_source", self._materialize_source),
            ("import_data", self._import_data),
            ("validate_data", self._validate_data),
        ]:
            step = self._run_required_step(name, action)
            if step.status == "FAILED":
                return self._finalize()

        self._run_optional_step("quality_report", self._quality_report, enabled=self.spec.run_quality_report)
        self._run_optional_step("audit_leakage", self._audit_leakage, enabled=self.spec.run_leakage_audit)
        self._run_optional_step("check_security", self._check_security, enabled=self.spec.run_security_check)
        self._run_optional_step("run_pipeline", self._run_pipeline, enabled=self.spec.run_pipeline)
        self._run_optional_step("build_frontend", self._build_frontend, enabled=self.spec.build_frontend)
        self._run_optional_step("build_dashboard", self._build_dashboard, enabled=self.spec.build_dashboard)
        self._run_optional_step("record_experiment", self._record_experiment, enabled=self.spec.record_experiment)
        return self._finalize()

    def _load_profile(self) -> SourceProfile:
        profile_path = Path(self.spec.source_profile)
        profile = SourceProfile.model_validate(load_yaml_config(profile_path))
        if profile.source_name != self.spec.source_name:
            raise ValueError(
                f"source_name mismatch: spec={self.spec.source_name}, profile={profile.source_name}"
            )
        if profile.requires_network:
            raise ValueError("real-data offline drill requires source_profile.requires_network=false")
        if profile.mode == "live_disabled":
            raise ValueError("real-data offline drill cannot use a live_disabled source profile")
        return profile

    def _cache_source_fixture(self) -> tuple[list[Path], dict[str, Any]]:
        profile = self._require_profile()
        if not profile.fixture_dir:
            raise ValueError("source profile must provide fixture_dir for offline drill")
        source_name = profile.contract_source_name
        store = ExternalCacheStore(cache_root=self.drill_dir / "cache", config_dir=self.config_dir)
        result = store.cache_source_fixture(
            source_name=source_name,
            fixture_dir=Path(profile.fixture_dir),
            cache_version=self.spec.data_version,
            overwrite=True,
        )
        if result.status == "FAILED":
            raise ValueError(result.error_message or "cache source fixture failed")
        self.cache_dir = Path(result.cache_dir)
        self.summary["cache"] = result.model_dump(mode="json")
        return [Path(result.manifest_path)], result.model_dump(mode="json")

    def _materialize_cache(self) -> tuple[list[Path], dict[str, Any]]:
        profile = self._require_profile()
        result = ExternalCacheStore(cache_root=self.drill_dir / "cache", config_dir=self.config_dir).materialize_cache(
            source_name=profile.contract_source_name,
            cache_version=self.spec.data_version,
            mapping_path=Path(profile.mapping_path),
        )
        if result.status != "NORMALIZED":
            raise ValueError(result.error_message or "materialize cache failed")
        self.summary["materialize_cache"] = result.model_dump(mode="json")
        return [Path(result.manifest_path), Path(result.normalized_dir)], result.model_dump(mode="json")

    def _materialize_source(self) -> tuple[list[Path], dict[str, Any]]:
        result = SourceMaterializer(
            profile_path=Path(self.spec.source_profile),
            config_dir=self.config_dir,
            output_root_dir=self.drill_dir / "materialized",
            data_version=self.spec.data_version,
            run_quality_report=self.spec.run_quality_report,
        ).run()
        if result.status != "SUCCESS":
            raise ValueError(result.error_message or "materialize source failed")
        self.materialized_data_dir = Path(result.output_dir)
        self.summary["materialized"] = result.model_dump(mode="json")
        output_paths = [Path(result.output_dir) / "materialization_result.json", Path(result.output_dir)]
        return output_paths, result.model_dump(mode="json")

    def _import_data(self) -> tuple[list[Path], dict[str, Any]]:
        if self.materialized_data_dir is None:
            raise RuntimeError("materialized_data_dir is not available")
        manifest = ImportJob(
            source_name=self.spec.source_name,
            source_data_dir=self.materialized_data_dir,
            target_root_dir=Path("data/imports"),
            data_version=self.spec.data_version,
            config_dir=self.config_dir,
            overwrite=True,
            notes=self.spec.notes,
            quality_report=self.spec.run_quality_report,
        ).run()
        self.imported_data_dir = Path(manifest.target_data_dir)
        self.summary["import"] = manifest.model_dump(mode="json")
        if manifest.status != "SUCCESS":
            raise ValueError(manifest.error_message or "import data failed")
        return [Path(manifest.target_data_dir) / "import_manifest.json", Path(manifest.target_data_dir)], {
            "status": manifest.status,
            "import_id": manifest.import_id,
            "target_data_dir": manifest.target_data_dir,
            "validation_passed": manifest.validation_passed,
            "row_counts": manifest.row_counts,
        }

    def _validate_data(self) -> tuple[list[Path], dict[str, Any]]:
        imported_dir = self._require_imported_data_dir()
        report = LocalCsvAdapter(imported_dir).validate_all()
        validation_dir = self.drill_dir / "validation"
        report_path = validation_dir / "validation_report.json"
        save_validation_report(report, report_path)
        self.validation_report_path = report_path
        self.summary["validation"] = report.model_dump(mode="json")
        if not report.passed:
            raise ValueError("validate data failed: " + "; ".join(report.errors))
        return [report_path], report.model_dump(mode="json")

    def _quality_report(self) -> tuple[list[Path], dict[str, Any]]:
        imported_dir = self._require_imported_data_dir()
        report = DataQualityReporter(
            data_dir=imported_dir,
            config_dir=self.config_dir,
            source_name=self.spec.source_name,
            data_version=self.spec.data_version,
            target_date=self.spec.target_date,
        ).run()
        output_dir = self.drill_dir / "quality"
        save_quality_report_json(report, output_dir / "quality_report.json")
        save_quality_report_md(report, output_dir / "quality_report.md")
        save_quality_issues_csv(report, output_dir / "quality_issues.csv")
        self.quality_report_dir = output_dir
        payload = report.model_dump(mode="json")
        self.summary["quality"] = payload
        if report.error_count > 0:
            raise ValueError("quality report found error-level issues")
        return [output_dir / "quality_report.json", output_dir / "quality_report.md", output_dir / "quality_issues.csv"], payload

    def _audit_leakage(self) -> tuple[list[Path], dict[str, Any]]:
        imported_dir = self._require_imported_data_dir()
        report = LeakageAuditor(
            data_dir=imported_dir,
            config_dir=self.config_dir,
            source_name=self.spec.source_name,
            data_version=self.spec.data_version,
        ).audit_for_date(self.spec.target_date)
        output_dir = self.drill_dir / "audit"
        save_leakage_audit_report_json(report, output_dir / "audit_report.json")
        save_leakage_audit_report_md(report, output_dir / "audit_report.md")
        self.leakage_audit_dir = output_dir
        payload = report.model_dump(mode="json")
        self.summary["leakage_audit"] = payload
        if report.error_count > 0:
            raise ValueError("leakage audit found error-level issues")
        return [output_dir / "audit_report.json", output_dir / "audit_report.md"], payload

    def _check_security(self) -> tuple[list[Path], dict[str, Any]]:
        report = ConfigSecurityScanner(self.config_dir).scan()
        output_dir = self.drill_dir / "security"
        save_security_scan_report_json(report, output_dir / "security_scan_report.json")
        save_security_scan_report_md(report, output_dir / "security_scan_report.md")
        self.security_report_dir = output_dir
        payload = report.model_dump(mode="json")
        self.summary["security"] = payload
        if report.error_count > 0:
            raise ValueError("security scan found error-level issues")
        return [output_dir / "security_scan_report.json", output_dir / "security_scan_report.md"], payload

    def _run_pipeline(self) -> tuple[list[Path], dict[str, Any]]:
        imported_dir = self._require_imported_data_dir()
        output_dir = self.drill_dir / "pipeline"
        manifest = PipelineRunner(
            date=self.spec.target_date,
            data_dir=imported_dir,
            config_dir=self.config_dir,
            output_dir=output_dir,
            audit_leakage=True,
            audit_source_name=self.spec.source_name,
            audit_data_version=self.spec.data_version,
            quality_report=True,
            check_security=True,
        ).run()
        self.pipeline_output_dir = output_dir
        payload = {
            "status": manifest.status,
            "total_stocks": manifest.total_stocks,
            "allowed_universe_count": manifest.allowed_universe_count,
            "buy_count": manifest.buy_count,
            "watch_count": manifest.watch_count,
            "block_count": manifest.block_count,
            "high_risk_count": manifest.high_risk_count,
            "market_regime": manifest.market_regime,
            "output_dir": str(output_dir),
        }
        self.summary["pipeline"] = payload
        if manifest.status == "FAILED":
            raise ValueError("pipeline failed; inspect pipeline/manifest.json")
        return [output_dir / "manifest.json", output_dir / "pipeline_summary.md"], payload

    def _build_frontend(self) -> tuple[list[Path], dict[str, Any]]:
        output_dir = self.drill_dir / "frontend"
        data = collect_frontend_data(self.drill_dir)
        save_frontend_site(data, output_dir)
        self.frontend_output_dir = output_dir
        payload = {
            "artifact_count": data.summary.get("artifact_count", 0),
            "warning_count": len(data.warning_items),
            "output_dir": str(output_dir),
        }
        self.summary["frontend"] = payload
        return [output_dir / "index.html", output_dir / "frontend_data.json"], payload

    def _build_dashboard(self) -> tuple[list[Path], dict[str, Any]]:
        output_dir = self.drill_dir / "dashboard"
        index = DashboardScanner(self.drill_dir).scan()
        summary = build_dashboard_summary(index)
        save_dashboard_index_json(index, output_dir / "dashboard_index.json")
        save_dashboard_summary_json(summary, output_dir / "dashboard_summary.json")
        save_dashboard_markdown(index, summary, output_dir / "dashboard.md")
        save_dashboard_tables(index, summary, output_dir / "dashboard_tables")
        self.dashboard_output_dir = output_dir
        payload = {
            "artifact_count": index.artifact_count,
            "warning_count": len(summary.warning_items),
            "output_dir": str(output_dir),
            "summary_text": summary.summary_text,
        }
        self.summary["dashboard"] = payload
        return [output_dir / "dashboard_index.json", output_dir / "dashboard_summary.json", output_dir / "dashboard.md"], payload

    def _record_experiment(self) -> tuple[list[Path], dict[str, Any]]:
        record = ExperimentRecorder(ExperimentRegistry(Path(self.spec.experiment_registry_dir))).record_completed_run(
            command="real-data-offline-drill",
            command_args={
                "drill_id": self.drill_id,
                "source_name": self.spec.source_name,
                "data_version": self.spec.data_version,
                "target_date": self.spec.target_date.isoformat(),
                "output_dir": self.drill_dir,
            },
            status=self._current_status(),
            output_dir=self.drill_dir,
            data_dir=self.imported_data_dir,
            config_dir=self.config_dir,
            notes=self.spec.notes,
            tags=["v0.3", "real-data-offline", self.spec.source_name],
        )
        self.experiment_id = record.experiment_id
        payload = {
            "experiment_id": record.experiment_id,
            "registry_dir": self.spec.experiment_registry_dir,
            "tags": record.tags,
        }
        self.summary["experiment"] = payload
        return [Path(self.spec.experiment_registry_dir) / "records" / f"{record.experiment_id}.json"], payload

    def _run_required_step(self, name: str, action: RequiredAction) -> RealDataOfflineDrillStep:
        step = self._run_step(name, action)
        if step.status == "FAILED":
            self._required_failed = True
        return step

    def _run_optional_step(self, name: str, action: RequiredAction, *, enabled: bool) -> RealDataOfflineDrillStep:
        if not enabled:
            step = _step(name, "SKIPPED", datetime.now(), summary={"reason": "disabled by drill spec"})
            self.steps.append(step)
            return step
        step = self._run_step(name, action)
        if step.status == "FAILED":
            self._optional_failed = True
        return step

    def _run_step(self, name: str, action: RequiredAction) -> RealDataOfflineDrillStep:
        started = datetime.now()
        try:
            output_paths, summary = action()
            step = _step(name, "SUCCESS", started, output_paths=output_paths, summary=summary)
        except Exception as exc:  # noqa: BLE001 - drill report must capture operational failures.
            step = _step(name, "FAILED", started, error_message=str(exc))
        self.steps.append(step)
        return step

    def _finalize(self) -> RealDataOfflineDrillResult:
        result = RealDataOfflineDrillResult(
            drill_id=self.drill_id,
            drill_name=self.spec.drill_name,
            generated_at=datetime.now(),
            source_name=self.spec.source_name,
            data_version=self.spec.data_version,
            target_date=self.spec.target_date,
            status=self._current_status(),
            steps=self.steps,
            output_dir=str(self.drill_dir),
            cache_dir=str(self.cache_dir) if self.cache_dir is not None else None,
            materialized_data_dir=str(self.materialized_data_dir) if self.materialized_data_dir is not None else None,
            imported_data_dir=str(self.imported_data_dir) if self.imported_data_dir is not None else None,
            validation_report_path=str(self.validation_report_path) if self.validation_report_path is not None else None,
            quality_report_dir=str(self.quality_report_dir) if self.quality_report_dir is not None else None,
            leakage_audit_dir=str(self.leakage_audit_dir) if self.leakage_audit_dir is not None else None,
            security_report_dir=str(self.security_report_dir) if self.security_report_dir is not None else None,
            pipeline_output_dir=str(self.pipeline_output_dir) if self.pipeline_output_dir is not None else None,
            frontend_output_dir=str(self.frontend_output_dir) if self.frontend_output_dir is not None else None,
            dashboard_output_dir=str(self.dashboard_output_dir) if self.dashboard_output_dir is not None else None,
            experiment_id=self.experiment_id,
            summary=self.summary,
        )
        save_realdata_offline_drill_artifacts(result, self.drill_dir)
        return result

    def _current_status(self) -> str:
        if self._required_failed:
            return "FAILED"
        if self._optional_failed:
            return "PARTIAL"
        return "SUCCESS"

    def _require_profile(self) -> SourceProfile:
        if self.profile is None:
            raise RuntimeError("source profile has not been loaded")
        return self.profile

    def _require_imported_data_dir(self) -> Path:
        if self.imported_data_dir is None:
            raise RuntimeError("imported_data_dir is not available")
        return self.imported_data_dir


def _step(
    name: str,
    status: str,
    started_at: datetime,
    output_paths: list[Path] | None = None,
    summary: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> RealDataOfflineDrillStep:
    finished_at = datetime.now()
    return RealDataOfflineDrillStep(
        name=name,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=(finished_at - started_at).total_seconds(),
        output_paths=[str(path) for path in output_paths or []],
        summary=summary or {},
        error_message=error_message,
    )


def _new_drill_id(spec: RealDataOfflineDrillSpec) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    source = normalize_source_name(spec.source_name)
    return f"{source}_{spec.data_version}_{timestamp}_{uuid.uuid4().hex[:8]}"
