from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

import yaml

from ashare_alpha.backtest import BacktestEngine, save_backtest_summary_md, save_daily_equity_csv, save_metrics_json, save_trades_csv
from ashare_alpha.config import load_project_config
from ashare_alpha.data import DailyBar, LocalCsvAdapter
from ashare_alpha.experiments import ExperimentRecorder, ExperimentRegistry
from ashare_alpha.sweeps import SweepRunner
from ashare_alpha.sweeps.storage import load_sweep_result_json
from ashare_alpha.walkforward.analysis import analyze_walkforward
from ashare_alpha.walkforward.models import WalkForwardFold, WalkForwardResult, WalkForwardSpec
from ashare_alpha.walkforward.splitter import generate_walkforward_folds
from ashare_alpha.walkforward.storage import (
    save_fold_metrics_csv,
    save_walkforward_result_json,
    save_walkforward_summary_md,
)


class WalkForwardRunner:
    def __init__(self, spec_path: Path, output_dir: Path | None = None) -> None:
        self.spec_path = Path(spec_path)
        self.output_root_override = Path(output_dir) if output_dir is not None else None

    def run(self) -> WalkForwardResult:
        spec = self._load_spec()
        walkforward_id = self._make_walkforward_id()
        output_root = self.output_root_override or Path(spec.output_root_dir)
        walkforward_output_dir = output_root / walkforward_id
        walkforward_output_dir.mkdir(parents=True, exist_ok=False)

        folds = generate_walkforward_folds(
            start_date=spec.start_date,
            end_date=spec.end_date,
            test_window_days=spec.test_window_days,
            step_days=spec.step_days,
            train_window_days=spec.train_window_days,
        )
        daily_bars = self._load_daily_bars(spec)
        completed_folds = [self._run_fold(spec, fold, walkforward_output_dir, daily_bars) for fold in folds]
        stability_metrics, overfit_warnings, summary = analyze_walkforward(completed_folds)
        result = self._build_result(spec, walkforward_id, completed_folds, stability_metrics, overfit_warnings, summary)

        save_walkforward_result_json(result, walkforward_output_dir / "walkforward_result.json")
        save_walkforward_summary_md(result, walkforward_output_dir / "walkforward_summary.md")
        save_fold_metrics_csv(result, walkforward_output_dir / "fold_metrics.csv")
        return result

    def _load_spec(self) -> WalkForwardSpec:
        if not self.spec_path.exists():
            raise ValueError(f"walkforward spec does not exist: {self.spec_path}")
        payload = yaml.safe_load(self.spec_path.read_text(encoding="utf-8"))
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError(f"walkforward spec must contain a YAML mapping: {self.spec_path}")
        return WalkForwardSpec.model_validate(payload)

    def _make_walkforward_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content = self.spec_path.read_bytes() if self.spec_path.exists() else str(self.spec_path).encode()
        digest = hashlib.sha256(content + timestamp.encode("utf-8")).hexdigest()[:8]
        return f"wf_{timestamp}_{digest}"

    def _load_daily_bars(self, spec: WalkForwardSpec) -> list[DailyBar]:
        adapter = LocalCsvAdapter(Path(spec.data_dir))
        validation_report = adapter.validate_all()
        if not validation_report.passed:
            raise ValueError("Data validation failed: " + "; ".join(validation_report.errors))
        return adapter.load_daily_bars()

    def _run_fold(
        self,
        spec: WalkForwardSpec,
        fold: WalkForwardFold,
        walkforward_output_dir: Path,
        daily_bars: list[DailyBar],
    ) -> WalkForwardFold:
        fold_dir = walkforward_output_dir / "folds" / f"fold_{fold.fold_index:03d}"
        fold_dir.mkdir(parents=True, exist_ok=True)
        trading_days = _count_trading_days(daily_bars, fold.test_start, fold.test_end)
        if trading_days < spec.min_test_trading_days:
            return fold.model_copy(
                update={
                    "status": "SKIPPED",
                    "output_dir": str(fold_dir),
                    "metrics": {"trading_days": trading_days},
                    "error_message": (
                        f"test window has {trading_days} trading days, below min_test_trading_days="
                        f"{spec.min_test_trading_days}"
                    ),
                }
            )

        try:
            if spec.command == "run-backtest":
                return self._run_backtest_fold(spec, fold, fold_dir)
            if spec.command == "run-sweep":
                return self._run_sweep_fold(spec, fold, fold_dir)
            raise ValueError(f"Unsupported walkforward command: {spec.command}")
        except Exception as exc:  # noqa: BLE001 - later folds should still run.
            return fold.model_copy(
                update={
                    "status": "FAILED",
                    "output_dir": str(fold_dir),
                    "error_message": str(exc),
                }
            )

    def _run_backtest_fold(self, spec: WalkForwardSpec, fold: WalkForwardFold, fold_dir: Path) -> WalkForwardFold:
        config = load_project_config(Path(spec.base_config_dir))
        adapter = LocalCsvAdapter(Path(spec.data_dir))
        result = BacktestEngine(
            config=config,
            stock_master=adapter.load_stock_master(),
            daily_bars=adapter.load_daily_bars(),
            financial_summary=adapter.load_financial_summary(),
            announcement_events=adapter.load_announcement_events(),
        ).run(fold.test_start, fold.test_end)
        save_trades_csv(result.trades, fold_dir / "trades.csv")
        save_daily_equity_csv(result.daily_equity, fold_dir / "daily_equity.csv")
        save_metrics_json(result.metrics, fold_dir / "metrics.json")
        save_backtest_summary_md(result, fold_dir / "summary.md")
        metrics = asdict(result.metrics)
        metrics["start_date"] = result.metrics.start_date.isoformat()
        metrics["end_date"] = result.metrics.end_date.isoformat()
        experiment_id = self._record_fold_experiment(
            spec=spec,
            fold=fold,
            status="SUCCESS",
            output_dir=fold_dir,
            metrics_args={
                "start": fold.test_start.isoformat(),
                "end": fold.test_end.isoformat(),
                **spec.common_args,
            },
        )
        return fold.model_copy(
            update={
                "status": "SUCCESS",
                "experiment_id": experiment_id,
                "output_dir": str(fold_dir),
                "metrics": metrics,
            }
        )

    def _run_sweep_fold(self, spec: WalkForwardSpec, fold: WalkForwardFold, fold_dir: Path) -> WalkForwardFold:
        if spec.sweep_spec is None:
            raise ValueError("sweep_spec is required when command=run-sweep")
        folded_spec_path = self._write_fold_sweep_spec(spec, fold, fold_dir)
        sweep_result = SweepRunner(folded_spec_path, output_dir=fold_dir / "sweep").run()
        metrics = _metrics_from_sweep_result(sweep_result.output_dir)
        experiment_id = self._record_fold_experiment(
            spec=spec,
            fold=fold,
            status="SUCCESS" if sweep_result.failed_count == 0 else "PARTIAL",
            output_dir=Path(sweep_result.output_dir),
            metrics_args={
                "sweep_spec": folded_spec_path,
                "start": fold.test_start.isoformat(),
                "end": fold.test_end.isoformat(),
                **spec.common_args,
            },
        )
        status = "SUCCESS" if sweep_result.failed_count == 0 else "PARTIAL"
        return fold.model_copy(
            update={
                "status": status,
                "experiment_id": experiment_id,
                "output_dir": sweep_result.output_dir,
                "metrics": metrics,
                "error_message": sweep_result.summary if status == "PARTIAL" else None,
            }
        )

    def _write_fold_sweep_spec(self, spec: WalkForwardSpec, fold: WalkForwardFold, fold_dir: Path) -> Path:
        path = Path(str(spec.sweep_spec))
        if not path.exists():
            raise ValueError(f"sweep_spec does not exist: {path}")
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"sweep_spec must contain a YAML mapping: {path}")
        common_args = dict(payload.get("common_args") or {})
        common_args.update(spec.common_args)
        common_args["start"] = fold.test_start.isoformat()
        common_args["end"] = fold.test_end.isoformat()
        payload["common_args"] = common_args
        payload["data_dir"] = spec.data_dir
        payload["base_config_dir"] = spec.base_config_dir
        payload["experiment_registry_dir"] = spec.experiment_registry_dir
        payload["output_root_dir"] = str(fold_dir / "sweep")
        folded_path = fold_dir / "fold_sweep_spec.yaml"
        folded_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return folded_path

    def _record_fold_experiment(
        self,
        spec: WalkForwardSpec,
        fold: WalkForwardFold,
        status: str,
        output_dir: Path,
        metrics_args: dict[str, object],
    ) -> str:
        tags = [*spec.tags, "walkforward", spec.name, f"fold_{fold.fold_index:03d}"]
        experiment = ExperimentRecorder(ExperimentRegistry(Path(spec.experiment_registry_dir))).record_completed_run(
            command=spec.command,
            command_args={
                **metrics_args,
                "data_dir": spec.data_dir,
                "config_dir": spec.base_config_dir,
                "output_dir": output_dir,
                "walkforward_name": spec.name,
                "fold_index": fold.fold_index,
                "train_start": fold.train_start.isoformat() if fold.train_start else None,
                "train_end": fold.train_end.isoformat() if fold.train_end else None,
            },
            status=status,
            output_dir=output_dir,
            data_dir=Path(spec.data_dir),
            config_dir=Path(spec.base_config_dir),
            notes=_notes_for_fold(spec, fold),
            tags=_dedupe(tags),
        )
        return experiment.experiment_id

    def _build_result(
        self,
        spec: WalkForwardSpec,
        walkforward_id: str,
        folds: list[WalkForwardFold],
        stability_metrics: dict[str, object],
        overfit_warnings: list[str],
        summary: str,
    ) -> WalkForwardResult:
        return WalkForwardResult(
            walkforward_id=walkforward_id,
            name=spec.name,
            command=spec.command,
            generated_at=datetime.now(),
            start_date=spec.start_date,
            end_date=spec.end_date,
            fold_count=len(folds),
            success_count=sum(1 for fold in folds if fold.status in {"SUCCESS", "PARTIAL"}),
            failed_count=sum(1 for fold in folds if fold.status == "FAILED"),
            skipped_count=sum(1 for fold in folds if fold.status == "SKIPPED"),
            folds=folds,
            stability_metrics=stability_metrics,
            overfit_warnings=overfit_warnings,
            summary=summary,
        )


def _count_trading_days(daily_bars: list[DailyBar], start_date: date, end_date: date) -> int:
    return len({bar.trade_date for bar in daily_bars if start_date <= bar.trade_date <= end_date and bar.is_trading})


def _metrics_from_sweep_result(output_dir: str) -> dict[str, object]:
    result_path = Path(output_dir) / "sweep_result.json"
    result = load_sweep_result_json(result_path)
    metrics: dict[str, object] = {
        "success_count": result.success_count,
        "failed_count": result.failed_count,
    }
    total_returns = [_as_float(run.metrics.get("total_return")) for run in result.runs]
    total_returns = [value for value in total_returns if value is not None]
    drawdowns = [_as_float(run.metrics.get("max_drawdown")) for run in result.runs]
    drawdowns = [value for value in drawdowns if value is not None]
    if total_returns:
        metrics["best_total_return"] = max(total_returns)
        metrics["mean_total_return"] = sum(total_returns) / len(total_returns)
        metrics["total_return"] = metrics["mean_total_return"]
    if drawdowns:
        metrics["worst_max_drawdown"] = min(drawdowns)
        metrics["max_drawdown"] = metrics["worst_max_drawdown"]
    return metrics


def _as_float(value: object) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def _notes_for_fold(spec: WalkForwardSpec, fold: WalkForwardFold) -> str:
    parts = [
        f"walkforward={spec.name}",
        f"fold={fold.fold_index}",
        f"test={fold.test_start.isoformat()}..{fold.test_end.isoformat()}",
    ]
    if spec.notes:
        parts.append(spec.notes)
    return "\n".join(parts)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result
