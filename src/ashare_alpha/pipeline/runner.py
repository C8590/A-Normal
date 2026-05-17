from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from ashare_alpha.audit import (
    LeakageAuditor,
    build_data_snapshot,
    save_data_snapshot_json,
    save_leakage_audit_report_json,
    save_leakage_audit_report_md,
)
from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.events import EventDailyRecord, EventFeatureBuilder, save_event_daily_csv, summarize_event_daily
from ashare_alpha.factors import FactorBuilder, FactorDailyRecord, save_factor_csv, summarize_factors
from ashare_alpha.pipeline.models import PIPELINE_DISCLAIMER, PipelineManifest, PipelineStepResult
from ashare_alpha.pipeline.storage import save_pipeline_manifest, save_pipeline_summary_md
from ashare_alpha.probability import (
    ProbabilityPredictionRecord,
    ProbabilityPredictor,
    load_probability_model_json,
    save_probability_predictions_csv,
)
from ashare_alpha.quality import (
    DataQualityReporter,
    save_quality_issues_csv,
    save_quality_report_json,
    save_quality_report_md,
)
from ashare_alpha.reports import DailyReportBuilder, save_daily_report
from ashare_alpha.security import ConfigSecurityScanner, save_security_scan_report_json, save_security_scan_report_md
from ashare_alpha.signals import SignalDailyRecord, SignalGenerator, save_signal_csv, summarize_signals
from ashare_alpha.universe import UniverseBuilder, UniverseDailyRecord, save_universe_csv, summarize_universe


class PipelineRunner:
    def __init__(
        self,
        date: date,
        data_dir: Path,
        config_dir: Path,
        output_dir: Path,
        model_dir: Path | None = None,
        require_probability: bool = False,
        audit_leakage: bool = False,
        audit_source_name: str = "local_csv",
        audit_data_version: str = "sample",
        quality_report: bool = False,
        check_security: bool = False,
    ) -> None:
        self.date = date
        self.data_dir = data_dir
        self.config_dir = config_dir
        self.output_dir = output_dir
        self.model_dir = model_dir
        self.require_probability = require_probability
        self.audit_leakage = audit_leakage
        self.audit_source_name = audit_source_name
        self.audit_data_version = audit_data_version
        self.quality_report = quality_report
        self.check_security = check_security
        self.steps: list[PipelineStepResult] = []
        self.config = None
        self.adapter: LocalCsvAdapter | None = None
        self.stock_master = []
        self.daily_bars = []
        self.financial_summary = []
        self.announcement_events = []
        self.universe_records: list[UniverseDailyRecord] = []
        self.factor_records: list[FactorDailyRecord] = []
        self.event_records: list[EventDailyRecord] = []
        self.signal_records: list[SignalDailyRecord] = []
        self.probability_predictions: list[ProbabilityPredictionRecord] = []
        self.paths: dict[str, Path] = {}

    def run(self) -> PipelineManifest:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self.check_security:
            security_step = self._run_security_step()
            if security_step.status == "FAILED":
                return self._finalize("FAILED")

        validate_step = self._run_step("validate_data", self._validate_data)
        if validate_step.status == "FAILED":
            return self._finalize("FAILED")

        if self.quality_report:
            quality_step = self._run_quality_step()
            if quality_step.status == "FAILED":
                return self._finalize("FAILED")

        if self.audit_leakage:
            audit_step = self._run_audit_step()
            if audit_step.status == "FAILED":
                return self._finalize("FAILED")

        for name, action in [
            ("build_universe", self._build_universe),
            ("compute_factors", self._compute_factors),
            ("compute_events", self._compute_events),
            ("generate_signals", self._generate_signals),
            ("daily_report", self._daily_report),
        ]:
            step = self._run_step(name, action)
            if step.status == "FAILED":
                return self._finalize("FAILED")

        probability_step = self._run_probability_step()
        if probability_step.status == "FAILED" and self.require_probability:
            return self._finalize("FAILED")
        if probability_step.status == "FAILED":
            return self._finalize("PARTIAL")
        return self._finalize("SUCCESS")

    def _run_step(self, name: str, action: Callable[[], tuple[list[Path], dict[str, object]]]) -> PipelineStepResult:
        started = datetime.now()
        try:
            output_paths, summary = action()
            step = _step(name, "SUCCESS", started, output_paths=output_paths, summary=summary)
        except Exception as exc:  # noqa: BLE001 - pipeline manifest needs to capture step failure details.
            step = _step(name, "FAILED", started, error_message=str(exc))
        self.steps.append(step)
        return step

    def _run_quality_step(self) -> PipelineStepResult:
        started = datetime.now()
        try:
            output_paths, summary = self._quality_report()
            error_count = int(summary.get("error_count", 0))
            if error_count > 0:
                step = _step(
                    "quality_report",
                    "FAILED",
                    started,
                    output_paths=output_paths,
                    summary=summary,
                    error_message="quality report found error-level issues",
                )
            else:
                step = _step("quality_report", "SUCCESS", started, output_paths=output_paths, summary=summary)
        except Exception as exc:  # noqa: BLE001 - pipeline manifest needs to capture quality failure details.
            step = _step("quality_report", "FAILED", started, error_message=str(exc))
        self.steps.append(step)
        return step

    def _run_security_step(self) -> PipelineStepResult:
        started = datetime.now()
        try:
            output_paths, summary = self._security_check()
            error_count = int(summary.get("error_count", 0))
            if error_count > 0:
                step = _step(
                    "security_check",
                    "FAILED",
                    started,
                    output_paths=output_paths,
                    summary=summary,
                    error_message="security scan found error-level issues",
                )
            else:
                step = _step("security_check", "SUCCESS", started, output_paths=output_paths, summary=summary)
        except Exception as exc:  # noqa: BLE001 - pipeline manifest needs to capture security failure details.
            step = _step("security_check", "FAILED", started, error_message=str(exc))
        self.steps.append(step)
        return step

    def _run_audit_step(self) -> PipelineStepResult:
        started = datetime.now()
        try:
            output_paths, summary = self._audit_leakage()
            error_count = int(summary.get("error_count", 0))
            if error_count > 0:
                step = _step(
                    "audit_leakage",
                    "FAILED",
                    started,
                    output_paths=output_paths,
                    summary=summary,
                    error_message="leakage audit found error-level issues",
                )
            else:
                step = _step("audit_leakage", "SUCCESS", started, output_paths=output_paths, summary=summary)
        except Exception as exc:  # noqa: BLE001 - pipeline manifest needs to capture audit failure details.
            step = _step("audit_leakage", "FAILED", started, error_message=str(exc))
        self.steps.append(step)
        return step

    def _run_probability_step(self) -> PipelineStepResult:
        if self.model_dir is None:
            started = datetime.now()
            step = _step(
                "predict_probabilities",
                "SKIPPED",
                started,
                summary={"reason": "未提供 model_dir，跳过概率预测"},
            )
            self.steps.append(step)
            return step
        return self._run_step("predict_probabilities", self._predict_probabilities)

    def _validate_data(self) -> tuple[list[Path], dict[str, object]]:
        self.config = load_project_config(self.config_dir)
        self.adapter = LocalCsvAdapter(self.data_dir)
        report = self.adapter.validate_all()
        if not report.passed:
            raise ValueError("数据校验失败：" + "；".join(report.errors))
        self.stock_master = self.adapter.load_stock_master()
        self.daily_bars = self.adapter.load_daily_bars()
        self.financial_summary = self.adapter.load_financial_summary()
        self.announcement_events = self.adapter.load_announcement_events()
        return [], {"passed": True, "total_stocks": len(self.stock_master)}

    def _audit_leakage(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        report = LeakageAuditor(
            data_dir=self.data_dir,
            config_dir=self.config_dir,
            source_name=self.audit_source_name,
            data_version=self.audit_data_version,
        ).audit_records(
            audit_date=self.date,
            start_date=None,
            end_date=None,
            stock_master=self.stock_master,
            daily_bars=self.daily_bars,
            financial_summary=self.financial_summary,
            announcement_events=self.announcement_events,
        )
        snapshot = build_data_snapshot(
            data_dir=self.data_dir,
            config_dir=self.config_dir,
            source_name=self.audit_source_name,
            data_version=self.audit_data_version,
            stock_master=self.stock_master,
            daily_bars=self.daily_bars,
            financial_summary=self.financial_summary,
            announcement_events=self.announcement_events,
        )
        audit_dir = self.output_dir / "audit"
        report_json = audit_dir / "audit_report.json"
        report_md = audit_dir / "audit_report.md"
        snapshot_json = audit_dir / "data_snapshot.json"
        save_leakage_audit_report_json(report, report_json)
        save_leakage_audit_report_md(report, report_md)
        save_data_snapshot_json(snapshot, snapshot_json)
        self.paths["leakage_audit"] = report_json
        return [report_json, report_md, snapshot_json], {
            "passed": report.passed,
            "total_issues": report.total_issues,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "info_count": report.info_count,
        }

    def _quality_report(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        report = DataQualityReporter(
            data_dir=self.data_dir,
            config_dir=self.config_dir,
            target_date=self.date,
        ).run()
        quality_dir = self.output_dir / "quality"
        report_json = quality_dir / "quality_report.json"
        report_md = quality_dir / "quality_report.md"
        issues_csv = quality_dir / "quality_issues.csv"
        save_quality_report_json(report, report_json)
        save_quality_report_md(report, report_md)
        save_quality_issues_csv(report, issues_csv)
        self.paths["quality_report"] = report_json
        return [report_json, report_md, issues_csv], {
            "passed": report.passed,
            "total_issues": report.total_issues,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "info_count": report.info_count,
        }

    def _security_check(self) -> tuple[list[Path], dict[str, object]]:
        load_project_config(self.config_dir)
        report = ConfigSecurityScanner(self.config_dir).scan()
        security_dir = self.output_dir / "security"
        report_json = security_dir / "security_scan_report.json"
        report_md = security_dir / "security_scan_report.md"
        save_security_scan_report_json(report, report_json)
        save_security_scan_report_md(report, report_md)
        self.paths["security_scan"] = report_json
        return [report_json, report_md], {
            "passed": report.passed,
            "total_issues": report.total_issues,
            "error_count": report.error_count,
            "warning_count": report.warning_count,
            "info_count": report.info_count,
        }

    def _build_universe(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        self.universe_records = UniverseBuilder(
            self.config,
            self.stock_master,
            self.daily_bars,
            self.financial_summary,
            self.announcement_events,
        ).build_for_date(self.date)
        path = self.output_dir / f"universe_daily_{self.date.isoformat()}.csv"
        save_universe_csv(self.universe_records, path)
        self.paths["universe"] = path
        return [path], summarize_universe(self.universe_records)

    def _compute_factors(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        self.factor_records = FactorBuilder(self.config, self.daily_bars, self.stock_master).build_for_date(self.date)
        path = self.output_dir / f"factor_daily_{self.date.isoformat()}.csv"
        save_factor_csv(self.factor_records, path)
        self.paths["factor"] = path
        return [path], summarize_factors(self.factor_records)

    def _compute_events(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        self.event_records = EventFeatureBuilder(self.config, self.announcement_events, self.stock_master).build_for_date(
            self.date
        )
        path = self.output_dir / f"event_daily_{self.date.isoformat()}.csv"
        save_event_daily_csv(self.event_records, path)
        self.paths["event"] = path
        return [path], summarize_event_daily(self.event_records)

    def _generate_signals(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        self.signal_records = SignalGenerator(
            self.config,
            self.stock_master,
            self.financial_summary,
            self.universe_records,
            self.factor_records,
            self.event_records,
        ).generate_for_date(self.date)
        path = self.output_dir / f"signal_daily_{self.date.isoformat()}.csv"
        save_signal_csv(self.signal_records, path)
        self.paths["signal"] = path
        return [path], summarize_signals(self.signal_records)

    def _daily_report(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        report = DailyReportBuilder(
            config=self.config,
            stock_master=self.stock_master,
            universe_records=self.universe_records,
            factor_records=self.factor_records,
            event_records=self.event_records,
            signal_records=self.signal_records,
            data_dir=self.data_dir,
            config_dir=self.config_dir,
        ).build(self.date)
        report_dir = self.output_dir / "daily_report"
        paths = save_daily_report(report, report_dir)
        self.paths["daily_report"] = paths["markdown"]
        return list(paths.values()), {
            "buy_count": report.buy_count,
            "watch_count": report.watch_count,
            "block_count": report.block_count,
            "high_risk_count": report.high_risk_count,
            "market_regime": report.market_regime,
        }

    def _predict_probabilities(self) -> tuple[list[Path], dict[str, object]]:
        self._require_loaded()
        if self.model_dir is None:
            raise ValueError("未提供 model_dir")
        model = load_probability_model_json(self.model_dir / "model.json")
        self.probability_predictions = ProbabilityPredictor(
            self.config,
            model,
            self.stock_master,
            self.daily_bars,
            self.financial_summary,
            self.announcement_events,
        ).predict_for_date(self.date)
        path = self.output_dir / f"probability_daily_{self.date.isoformat()}.csv"
        save_probability_predictions_csv(self.probability_predictions, path)
        self.paths["probability"] = path
        predictable = sum(1 for item in self.probability_predictions if item.is_predictable)
        return [path], {
            "total_stocks": len(self.probability_predictions),
            "predictable_count": predictable,
            "low_confidence_count": sum(1 for item in self.probability_predictions if item.confidence_level == "low"),
        }

    def _manifest(self, status: str) -> PipelineManifest:
        signal_summary = summarize_signals(self.signal_records) if self.signal_records else {}
        universe_summary = summarize_universe(self.universe_records) if self.universe_records else {}
        return PipelineManifest(
            pipeline_date=self.date,
            generated_at=datetime.now(),
            data_dir=str(self.data_dir),
            config_dir=str(self.config_dir),
            output_dir=str(self.output_dir),
            model_dir=str(self.model_dir) if self.model_dir is not None else None,
            status=status,
            steps=self.steps,
            total_stocks=len(self.stock_master) if self.stock_master else None,
            allowed_universe_count=universe_summary.get("allowed"),
            buy_count=signal_summary.get("buy"),
            watch_count=signal_summary.get("watch"),
            block_count=signal_summary.get("block"),
            high_risk_count=signal_summary.get("high_risk"),
            market_regime=signal_summary.get("market_regime"),
            probability_predictable_count=sum(1 for item in self.probability_predictions if item.is_predictable)
            if self.probability_predictions
            else None,
            daily_report_path=str(self.paths["daily_report"]) if "daily_report" in self.paths else None,
            universe_csv_path=str(self.paths["universe"]) if "universe" in self.paths else None,
            factor_csv_path=str(self.paths["factor"]) if "factor" in self.paths else None,
            event_csv_path=str(self.paths["event"]) if "event" in self.paths else None,
            signal_csv_path=str(self.paths["signal"]) if "signal" in self.paths else None,
            probability_csv_path=str(self.paths["probability"]) if "probability" in self.paths else None,
            leakage_audit_path=str(self.paths["leakage_audit"]) if "leakage_audit" in self.paths else None,
            quality_report_path=str(self.paths["quality_report"]) if "quality_report" in self.paths else None,
            security_scan_path=str(self.paths["security_scan"]) if "security_scan" in self.paths else None,
            disclaimer=PIPELINE_DISCLAIMER,
        )

    def _finalize(self, status: str) -> PipelineManifest:
        manifest = self._manifest(status)
        save_pipeline_manifest(manifest, self.output_dir / "manifest.json")
        save_pipeline_summary_md(manifest, self.output_dir / "pipeline_summary.md")
        return manifest

    def _require_loaded(self) -> None:
        if self.config is None or self.adapter is None:
            raise RuntimeError("pipeline data has not been validated and loaded")


def _step(
    name: str,
    status: str,
    started_at: datetime,
    output_paths: list[Path] | None = None,
    summary: dict[str, object] | None = None,
    error_message: str | None = None,
) -> PipelineStepResult:
    finished_at = datetime.now()
    return PipelineStepResult(
        name=name,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=(finished_at - started_at).total_seconds(),
        output_paths=[str(path) for path in output_paths or []],
        summary=summary or {},
        error_message=error_message,
    )
