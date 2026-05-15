from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

import yaml

from ashare_alpha.backtest import BacktestEngine, save_backtest_summary_md, save_daily_equity_csv, save_metrics_json, save_trades_csv
from ashare_alpha.config import load_project_config
from ashare_alpha.data import LocalCsvAdapter
from ashare_alpha.experiments import ExperimentRecorder, ExperimentRegistry
from ashare_alpha.pipeline import PipelineRunner
from ashare_alpha.probability import (
    ProbabilityTrainer,
    save_probability_dataset_csv,
    save_probability_metrics_json,
    save_probability_model_json,
    save_probability_predictions_csv,
    save_probability_summary_md,
)
from ashare_alpha.sweeps.config_overlay import apply_config_overrides, copy_config_dir
from ashare_alpha.sweeps.metrics_table import build_metrics_table
from ashare_alpha.sweeps.models import SweepResult, SweepRunRecord, SweepSpec, SweepVariant
from ashare_alpha.sweeps.storage import save_metrics_table_csv, save_sweep_result_json, save_sweep_summary_md


_COMMON_ARG_NAMES = {
    "run-pipeline": {
        "date",
        "data_dir",
        "model_dir",
        "require_probability",
        "audit_leakage",
        "quality_report",
        "check_security",
    },
    "run-backtest": {"start", "end", "data_dir"},
    "train-probability-model": {"start", "end", "data_dir"},
}


class SweepRunner:
    def __init__(self, spec_path: Path, output_dir: Path | None = None) -> None:
        self.spec_path = Path(spec_path)
        self.output_root_override = Path(output_dir) if output_dir is not None else None

    def run(self) -> SweepResult:
        spec = self._load_spec()
        sweep_id = self._make_sweep_id()
        output_root = self.output_root_override or Path(spec.output_root_dir)
        sweep_output_dir = output_root / sweep_id
        sweep_output_dir.mkdir(parents=True, exist_ok=False)
        runs: list[SweepRunRecord] = []

        for variant in spec.variants:
            runs.append(self._run_variant(spec, variant, sweep_output_dir))

        result = self._build_result(spec, sweep_id, sweep_output_dir, runs)
        save_sweep_result_json(result, sweep_output_dir / "sweep_result.json")
        rows = build_metrics_table(result)
        save_metrics_table_csv(rows, sweep_output_dir / "metrics_table.csv")
        save_sweep_summary_md(result, sweep_output_dir / "sweep_summary.md")
        return result

    def _load_spec(self) -> SweepSpec:
        if not self.spec_path.exists():
            raise ValueError(f"sweep spec does not exist: {self.spec_path}")
        payload = yaml.safe_load(self.spec_path.read_text(encoding="utf-8"))
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError(f"sweep spec must contain a YAML mapping: {self.spec_path}")
        return SweepSpec.model_validate(payload)

    def _make_sweep_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = self.spec_path.read_bytes() if self.spec_path.exists() else str(self.spec_path).encode()
        digest = hashlib.sha256(content + timestamp.encode("utf-8")).hexdigest()[:8]
        return f"sweep_{timestamp}_{digest}"

    def _run_variant(self, spec: SweepSpec, variant: SweepVariant, sweep_output_dir: Path) -> SweepRunRecord:
        started_at = datetime.now()
        variant_dir = sweep_output_dir / "variants" / variant.name
        config_dir = variant_dir / "config"
        output_dir = variant_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        experiment_id: str | None = None
        metrics: dict[str, object] = {}
        status = "FAILED"
        error_message: str | None = None

        try:
            copy_config_dir(Path(spec.base_config_dir), config_dir)
            config_changes = apply_config_overrides(config_dir, variant.config_overrides)
            _save_config_changes(config_changes, variant_dir)
            command_args = self._merged_command_args(spec, variant)
            status, metrics = self._run_command(spec.command, command_args, config_dir, output_dir)
            experiment_id = self._record_experiment(spec, variant, status, command_args, config_dir, output_dir)
        except Exception as exc:  # noqa: BLE001 - a sweep must keep later variants running.
            error_message = str(exc)
            try:
                if not config_dir.exists() and Path(spec.base_config_dir).exists():
                    copy_config_dir(Path(spec.base_config_dir), config_dir)
                experiment_id = self._record_experiment(
                    spec,
                    variant,
                    "FAILED",
                    self._safe_merged_command_args(spec, variant),
                    config_dir,
                    output_dir,
                )
            except Exception:  # noqa: BLE001 - preserve the original variant failure.
                experiment_id = None

        finished_at = datetime.now()
        return SweepRunRecord(
            variant_name=variant.name,
            status=status,
            experiment_id=experiment_id,
            config_dir=str(config_dir),
            output_dir=str(output_dir),
            metrics=metrics,
            error_message=error_message,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=(finished_at - started_at).total_seconds(),
        )

    def _merged_command_args(self, spec: SweepSpec, variant: SweepVariant) -> dict[str, object]:
        command_args: dict[str, object] = dict(spec.common_args)
        command_args.update(variant.command_args or {})
        invalid = sorted(set(command_args) - _COMMON_ARG_NAMES[spec.command])
        if invalid:
            raise ValueError(f"Unsupported command_args for {spec.command}: {', '.join(invalid)}")
        if spec.data_dir is not None and "data_dir" not in command_args:
            command_args["data_dir"] = spec.data_dir
        return command_args

    def _safe_merged_command_args(self, spec: SweepSpec, variant: SweepVariant) -> dict[str, object]:
        try:
            return self._merged_command_args(spec, variant)
        except ValueError:
            command_args = dict(spec.common_args)
            command_args.update(variant.command_args or {})
            if spec.data_dir is not None and "data_dir" not in command_args:
                command_args["data_dir"] = spec.data_dir
            return command_args

    def _run_command(
        self,
        command: str,
        command_args: dict[str, object],
        config_dir: Path,
        output_dir: Path,
    ) -> tuple[str, dict[str, object]]:
        if command == "run-pipeline":
            return self._run_pipeline(command_args, config_dir, output_dir)
        if command == "run-backtest":
            return self._run_backtest(command_args, config_dir, output_dir)
        if command == "train-probability-model":
            return self._run_probability_model(command_args, config_dir, output_dir)
        raise ValueError(f"Unsupported sweep command: {command}")

    def _run_pipeline(
        self,
        command_args: dict[str, object],
        config_dir: Path,
        output_dir: Path,
    ) -> tuple[str, dict[str, object]]:
        pipeline_date = _parse_required_date(command_args, "date")
        data_dir = _required_path(command_args, "data_dir")
        model_dir = _optional_path(command_args.get("model_dir"))
        manifest = PipelineRunner(
            date=pipeline_date,
            data_dir=data_dir,
            config_dir=config_dir,
            output_dir=output_dir,
            model_dir=model_dir,
            require_probability=bool(command_args.get("require_probability", False)),
            audit_leakage=bool(command_args.get("audit_leakage", False)),
            quality_report=bool(command_args.get("quality_report", False)),
            check_security=bool(command_args.get("check_security", False)),
        ).run()
        metrics = {
            "total_stocks": manifest.total_stocks,
            "allowed_universe_count": manifest.allowed_universe_count,
            "buy_count": manifest.buy_count,
            "watch_count": manifest.watch_count,
            "block_count": manifest.block_count,
            "high_risk_count": manifest.high_risk_count,
            "probability_predictable_count": manifest.probability_predictable_count,
        }
        return manifest.status, metrics

    def _run_backtest(
        self,
        command_args: dict[str, object],
        config_dir: Path,
        output_dir: Path,
    ) -> tuple[str, dict[str, object]]:
        start_date = _parse_required_date(command_args, "start")
        end_date = _parse_required_date(command_args, "end")
        if start_date >= end_date:
            raise ValueError("start must be earlier than end")
        config = load_project_config(config_dir)
        adapter = LocalCsvAdapter(_required_path(command_args, "data_dir"))
        validation_report = adapter.validate_all()
        if not validation_report.passed:
            raise ValueError("Data validation failed: " + "; ".join(validation_report.errors))
        result = BacktestEngine(
            config=config,
            stock_master=adapter.load_stock_master(),
            daily_bars=adapter.load_daily_bars(),
            financial_summary=adapter.load_financial_summary(),
            announcement_events=adapter.load_announcement_events(),
        ).run(start_date, end_date)
        save_trades_csv(result.trades, output_dir / "trades.csv")
        save_daily_equity_csv(result.daily_equity, output_dir / "daily_equity.csv")
        save_metrics_json(result.metrics, output_dir / "metrics.json")
        save_backtest_summary_md(result, output_dir / "summary.md")
        payload = asdict(result.metrics)
        payload["start_date"] = result.metrics.start_date.isoformat()
        payload["end_date"] = result.metrics.end_date.isoformat()
        return "SUCCESS", payload

    def _run_probability_model(
        self,
        command_args: dict[str, object],
        config_dir: Path,
        output_dir: Path,
    ) -> tuple[str, dict[str, object]]:
        start_date = _parse_required_date(command_args, "start")
        end_date = _parse_required_date(command_args, "end")
        if start_date >= end_date:
            raise ValueError("start must be earlier than end")
        config = load_project_config(config_dir)
        adapter = LocalCsvAdapter(_required_path(command_args, "data_dir"))
        validation_report = adapter.validate_all()
        if not validation_report.passed:
            raise ValueError("Data validation failed: " + "; ".join(validation_report.errors))
        trainer = ProbabilityTrainer(
            config=config,
            stock_master=adapter.load_stock_master(),
            daily_bars=adapter.load_daily_bars(),
            financial_summary=adapter.load_financial_summary(),
            announcement_events=adapter.load_announcement_events(),
        )
        result = trainer.train(start_date, end_date)
        if config.probability.output.save_dataset:
            save_probability_dataset_csv(trainer.last_dataset, output_dir / "probability_dataset.csv")
        if config.probability.output.save_model:
            save_probability_model_json(result.model, output_dir / "model.json")
        if config.probability.output.save_metrics:
            save_probability_metrics_json(result.metrics, output_dir / "metrics.json")
        if config.probability.output.save_test_predictions:
            save_probability_predictions_csv(trainer.last_test_predictions, output_dir / "test_predictions.csv")
        save_probability_summary_md(result, output_dir / "summary.md")
        metrics: dict[str, object] = {
            "dataset_rows": result.dataset_rows,
            "train_rows": result.train_rows,
            "test_rows": result.test_rows,
        }
        for metric in result.metrics:
            metrics[f"auc_{metric.horizon}d"] = metric.auc
            metrics[f"brier_score_{metric.horizon}d"] = metric.brier_score
            metrics[f"actual_win_rate_{metric.horizon}d"] = metric.actual_win_rate
        return "SUCCESS", metrics

    def _record_experiment(
        self,
        spec: SweepSpec,
        variant: SweepVariant,
        status: str,
        command_args: dict[str, object],
        config_dir: Path,
        output_dir: Path,
    ) -> str:
        tags = [*spec.tags, *variant.tags, "sweep", spec.sweep_name, variant.name]
        experiment = ExperimentRecorder(ExperimentRegistry(Path(spec.experiment_registry_dir))).record_completed_run(
            command=spec.command,
            command_args={
                **command_args,
                "config_dir": config_dir,
                "output_dir": output_dir,
                "sweep_name": spec.sweep_name,
                "variant_name": variant.name,
            },
            status=status,
            output_dir=output_dir,
            data_dir=_optional_path(command_args.get("data_dir")),
            config_dir=config_dir,
            notes=_notes_for_variant(spec, variant),
            tags=_dedupe(tags),
        )
        return experiment.experiment_id

    def _build_result(self, spec: SweepSpec, sweep_id: str, output_dir: Path, runs: list[SweepRunRecord]) -> SweepResult:
        success_count = sum(1 for run in runs if run.status == "SUCCESS")
        partial_count = sum(1 for run in runs if run.status == "PARTIAL")
        failed_count = sum(1 for run in runs if run.status == "FAILED")
        if failed_count == len(runs):
            summary = "所有 variant 均运行失败，请查看各 variant 的 error_message。"
        elif failed_count:
            summary = "部分 variant 失败，其余 variant 已完成并登记实验。"
        elif partial_count:
            summary = "Sweep 完成，但存在 PARTIAL variant，请查看对应输出。"
        else:
            summary = "Sweep 已完成，所有 variant 均成功。"
        return SweepResult(
            sweep_id=sweep_id,
            sweep_name=spec.sweep_name,
            command=spec.command,
            generated_at=datetime.now(),
            base_config_dir=spec.base_config_dir,
            output_dir=str(output_dir),
            registry_dir=spec.experiment_registry_dir,
            total_variants=len(runs),
            success_count=success_count,
            partial_count=partial_count,
            failed_count=failed_count,
            runs=runs,
            summary=summary,
        )


def _save_config_changes(changes: list[str], variant_dir: Path) -> None:
    (variant_dir / "config_changes.json").write_text(
        json.dumps(changes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = ["# Config Changes", ""]
    lines.extend(f"- {change}" for change in changes)
    if not changes:
        lines.append("- No config overrides")
    (variant_dir / "config_changes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_required_date(command_args: dict[str, object], key: str) -> date:
    value = command_args.get(key)
    if not isinstance(value, str):
        raise ValueError(f"command_args.{key} is required and must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc


def _required_path(command_args: dict[str, object], key: str) -> Path:
    value = command_args.get(key)
    path = _optional_path(value)
    if path is None:
        raise ValueError(f"command_args.{key} is required")
    return path


def _optional_path(value: object) -> Path | None:
    if value is None or value == "":
        return None
    return Path(str(value))


def _notes_for_variant(spec: SweepSpec, variant: SweepVariant) -> str:
    parts = [f"sweep={spec.sweep_name}", f"variant={variant.name}"]
    if spec.notes:
        parts.append(spec.notes)
    if variant.description:
        parts.append(variant.description)
    return "\n".join(parts)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
