from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path

import ashare_alpha as ashare_alpha_package
from ashare_alpha import __version__
from ashare_alpha.audit import (
    LeakageAuditor,
    build_data_snapshot,
    save_data_snapshot_json,
    save_leakage_audit_report_json,
    save_leakage_audit_report_md,
)
from ashare_alpha.backtest import (
    BacktestEngine,
    BacktestMetrics,
    BacktestResult,
    DailyEquityRecord,
    SimulatedTrade,
    save_backtest_summary_md,
    save_daily_equity_csv,
    save_metrics_json,
    save_trades_csv,
)
from ashare_alpha.config import ConfigError, load_project_config, load_yaml_config
from ashare_alpha.candidates import (
    CandidateSelector,
    load_candidate_selection_report_json,
    promote_candidate_config,
    save_candidate_scores_csv,
    save_candidate_selection_report_json,
    save_candidate_selection_report_md,
)
from ashare_alpha.data import DataSourceMetadata, LocalCsvAdapter, get_default_data_source_registry
from ashare_alpha.dashboard import (
    DashboardScanner,
    build_dashboard_summary,
    load_dashboard_index_json,
    load_dashboard_summary_json,
    save_dashboard_index_json,
    save_dashboard_markdown,
    save_dashboard_summary_json,
    save_dashboard_tables,
)
from ashare_alpha.data.contracts import (
    ExternalContractValidator,
    ExternalFixtureConverter,
    save_contract_report_json,
    save_contract_report_md,
    save_conversion_result_json,
)
from ashare_alpha.data.runtime import SourceMaterializer, SourceProfile, SourceRuntimeContext
from ashare_alpha.events import EventFeatureBuilder, save_event_daily_csv, summarize_event_daily
from ashare_alpha.experiments import (
    ExperimentRecorder,
    ExperimentRegistry,
    compare_experiments,
    save_compare_result_json,
    save_compare_result_md,
)
from ashare_alpha.factors import FactorBuilder, save_factor_csv, summarize_factors
from ashare_alpha.frontend import collect_frontend_data, host_warning, save_frontend_site, serve_frontend
from ashare_alpha.importing import ImportJob, load_import_manifest, normalize_source_name, validate_data_version
from ashare_alpha.pipeline import PipelineRunner, save_pipeline_manifest, save_pipeline_summary_md
from ashare_alpha.probability import (
    ProbabilityPredictor,
    ProbabilityTrainer,
    load_probability_model_json,
    save_probability_dataset_csv,
    save_probability_metrics_json,
    save_probability_model_json,
    save_probability_predictions_csv,
    save_probability_summary_md,
)
from ashare_alpha.quality import (
    DataQualityReporter,
    save_quality_issues_csv,
    save_quality_report_json,
    save_quality_report_md,
)
from ashare_alpha.release import ReleaseChecker, save_release_checklist_md, save_release_manifest_json
from ashare_alpha.reports import (
    BacktestReportBuilder,
    DailyReportBuilder,
    save_backtest_report,
    save_daily_report,
)
from ashare_alpha.security import (
    ConfigSecurityScanner,
    EnvSecretProvider,
    NetworkGuard,
    redact_mapping,
    safe_env_status,
    save_security_scan_report_json,
    save_security_scan_report_md,
)
from ashare_alpha.signals import SignalGenerator, save_signal_csv, summarize_signals
from ashare_alpha.sweeps import SweepRunner, build_metrics_table, load_sweep_result_json
from ashare_alpha.universe import UniverseBuilder, save_universe_csv, summarize_universe
from ashare_alpha.walkforward import WalkForwardRunner, load_walkforward_result_json


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sample" / "ashare_alpha"
_SWEEP_BASE_ROW_KEYS = {"variant_name", "status", "experiment_id", "output_dir", "duration_seconds"}


def build_parser() -> argparse.ArgumentParser:
    """Build the ashare-alpha-lab command line parser."""

    parser = argparse.ArgumentParser(
        prog="python -m ashare_alpha",
        description=(
            "A-share individual stock research lab for offline research, backtesting, "
            "signal generation, and reports. It does not place real orders."
        ),
    )
    parser.add_argument("--version", action="version", version=f"ashare-alpha-lab {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    show_version_parser = subparsers.add_parser("show-version", help="Show package and release version.")
    show_version_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    show_version_parser.set_defaults(handler=_cmd_show_version)

    release_check_parser = subparsers.add_parser("release-check", help="Run local MVP release checks.")
    release_check_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/release/v{version}.",
    )
    release_check_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    release_check_parser.set_defaults(handler=_cmd_release_check)

    show_config_parser = subparsers.add_parser("show-config", help="Load, validate, and print project config.")
    show_config_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    show_config_parser.set_defaults(handler=_cmd_show_config)

    validate_data_parser = subparsers.add_parser("validate-data", help="Validate local CSV sample data.")
    validate_data_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    validate_data_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    validate_data_parser.set_defaults(handler=_cmd_validate_data)

    list_sources_parser = subparsers.add_parser("list-data-sources", help="List registered data sources.")
    list_sources_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    list_sources_parser.set_defaults(handler=_cmd_list_data_sources)

    inspect_source_parser = subparsers.add_parser("inspect-data-source", help="Inspect one registered data source.")
    inspect_source_parser.add_argument("--name", required=True, help="Data source name, such as local_csv.")
    inspect_source_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    inspect_source_parser.set_defaults(handler=_cmd_inspect_data_source)

    list_source_profiles_parser = subparsers.add_parser("list-source-profiles", help="List external source runtime profiles.")
    list_source_profiles_parser.add_argument(
        "--profiles-dir",
        type=Path,
        default=Path("configs/ashare_alpha/source_profiles"),
        help="Directory containing source profile YAML files. Default: configs/ashare_alpha/source_profiles.",
    )
    list_source_profiles_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    list_source_profiles_parser.set_defaults(handler=_cmd_list_source_profiles)

    inspect_source_profile_parser = subparsers.add_parser(
        "inspect-source-profile",
        help="Inspect one external source runtime profile.",
    )
    inspect_source_profile_parser.add_argument("--profile", type=Path, required=True, help="Source profile YAML path.")
    inspect_source_profile_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    inspect_source_profile_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    inspect_source_profile_parser.set_defaults(handler=_cmd_inspect_source_profile)

    record_experiment_parser = subparsers.add_parser("record-experiment", help="Record an already completed research run.")
    record_experiment_parser.add_argument("--command", required=True, help="Command name, such as run-pipeline.")
    record_experiment_parser.add_argument("--output-dir", type=Path, required=True, help="Existing command output directory.")
    record_experiment_parser.add_argument("--data-dir", type=Path, default=None, help="Optional data directory used by the run.")
    record_experiment_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    record_experiment_parser.add_argument(
        "--status",
        choices=["SUCCESS", "PARTIAL", "FAILED"],
        default="SUCCESS",
        help="Run status. Default: SUCCESS.",
    )
    record_experiment_parser.add_argument("--notes", default=None, help="Optional experiment notes.")
    record_experiment_parser.add_argument("--tag", action="append", default=[], help="Experiment tag. Can be repeated.")
    record_experiment_parser.add_argument(
        "--registry-dir",
        type=Path,
        default=Path("outputs/experiments"),
        help="Experiment registry directory. Default: outputs/experiments.",
    )
    record_experiment_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    record_experiment_parser.set_defaults(handler=_cmd_record_experiment)

    list_experiments_parser = subparsers.add_parser("list-experiments", help="List recorded experiments.")
    list_experiments_parser.add_argument(
        "--registry-dir",
        type=Path,
        default=Path("outputs/experiments"),
        help="Experiment registry directory. Default: outputs/experiments.",
    )
    list_experiments_parser.add_argument("--command", default=None, help="Optional command filter.")
    list_experiments_parser.add_argument("--tag", default=None, help="Optional tag filter.")
    list_experiments_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    list_experiments_parser.set_defaults(handler=_cmd_list_experiments)

    show_experiment_parser = subparsers.add_parser("show-experiment", help="Show one recorded experiment.")
    show_experiment_parser.add_argument("--id", required=True, help="Experiment id.")
    show_experiment_parser.add_argument(
        "--registry-dir",
        type=Path,
        default=Path("outputs/experiments"),
        help="Experiment registry directory. Default: outputs/experiments.",
    )
    show_experiment_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    show_experiment_parser.set_defaults(handler=_cmd_show_experiment)

    compare_experiments_parser = subparsers.add_parser("compare-experiments", help="Compare two recorded experiments.")
    compare_experiments_parser.add_argument("--baseline", required=True, help="Baseline experiment id.")
    compare_experiments_parser.add_argument("--target", required=True, help="Target experiment id.")
    compare_experiments_parser.add_argument(
        "--registry-dir",
        type=Path,
        default=Path("outputs/experiments"),
        help="Experiment registry directory. Default: outputs/experiments.",
    )
    compare_experiments_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Comparison output directory. Defaults to outputs/experiments/comparisons.",
    )
    compare_experiments_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    compare_experiments_parser.set_defaults(handler=_cmd_compare_experiments)

    run_sweep_parser = subparsers.add_parser("run-sweep", help="Run a batch sweep from a sweep YAML spec.")
    run_sweep_parser.add_argument("--spec", type=Path, required=True, help="Sweep YAML spec path.")
    run_sweep_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional sweep output root directory. Defaults to spec.output_root_dir.",
    )
    run_sweep_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    run_sweep_parser.set_defaults(handler=_cmd_run_sweep)

    show_sweep_parser = subparsers.add_parser("show-sweep", help="Show a completed sweep_result.json.")
    show_sweep_parser.add_argument("--path", type=Path, required=True, help="Path to sweep_result.json.")
    show_sweep_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    show_sweep_parser.set_defaults(handler=_cmd_show_sweep)

    run_walkforward_parser = subparsers.add_parser(
        "run-walkforward",
        help="Run walk-forward out-of-sample validation from a YAML spec.",
    )
    run_walkforward_parser.add_argument("--spec", type=Path, required=True, help="Walk-forward YAML spec path.")
    run_walkforward_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional walk-forward output root directory. Defaults to spec.output_root_dir.",
    )
    run_walkforward_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    run_walkforward_parser.set_defaults(handler=_cmd_run_walkforward)

    show_walkforward_parser = subparsers.add_parser(
        "show-walkforward",
        help="Show a completed walkforward_result.json.",
    )
    show_walkforward_parser.add_argument("--path", type=Path, required=True, help="Path to walkforward_result.json.")
    show_walkforward_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    show_walkforward_parser.set_defaults(handler=_cmd_show_walkforward)

    select_candidates_parser = subparsers.add_parser(
        "select-candidates",
        help="Evaluate sweep, walk-forward, or experiment candidates for research promotion.",
    )
    select_candidates_parser.add_argument("--source", type=Path, action="append", required=True, help="Candidate source path. Can be repeated.")
    select_candidates_parser.add_argument(
        "--rules",
        type=Path,
        default=Path("configs/ashare_alpha/candidates/default_candidate_rules.yaml"),
        help="Candidate rules YAML path. Default: configs/ashare_alpha/candidates/default_candidate_rules.yaml.",
    )
    select_candidates_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/candidates/selection_YYYYMMDD_HHMMSS.",
    )
    select_candidates_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    select_candidates_parser.set_defaults(handler=_cmd_select_candidates)

    promote_candidate_parser = subparsers.add_parser(
        "promote-candidate-config",
        help="Copy a candidate config snapshot for the next research round.",
    )
    promote_candidate_parser.add_argument("--selection", type=Path, required=True, help="Path to candidate_selection.json.")
    promote_candidate_parser.add_argument("--candidate-id", required=True, help="Candidate id from candidate_selection.json.")
    promote_candidate_parser.add_argument("--promoted-name", required=True, help="Snapshot directory name.")
    promote_candidate_parser.add_argument(
        "--target-root",
        type=Path,
        default=Path("outputs/candidate_configs"),
        help="Target root for promoted config snapshots. Default: outputs/candidate_configs.",
    )
    promote_candidate_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing promoted snapshot.")
    promote_candidate_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    promote_candidate_parser.set_defaults(handler=_cmd_promote_candidate_config)

    build_dashboard_parser = subparsers.add_parser(
        "build-dashboard",
        help="Build a static read-only dashboard from research outputs.",
    )
    build_dashboard_parser.add_argument(
        "--outputs-root",
        type=Path,
        default=Path("outputs"),
        help="Research outputs root. Default: outputs.",
    )
    build_dashboard_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Dashboard output directory. Defaults to outputs/dashboard/dashboard_YYYYMMDD_HHMMSS.",
    )
    build_dashboard_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    build_dashboard_parser.set_defaults(handler=_cmd_build_dashboard)

    show_dashboard_parser = subparsers.add_parser("show-dashboard", help="Show a generated dashboard summary.")
    show_dashboard_parser.add_argument(
        "--path",
        type=Path,
        required=True,
        help="Dashboard output directory, dashboard_index.json, or dashboard_summary.json.",
    )
    show_dashboard_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    show_dashboard_parser.set_defaults(handler=_cmd_show_dashboard)

    build_frontend_parser = subparsers.add_parser(
        "build-frontend",
        help="Build a read-only static research frontend from outputs.",
    )
    build_frontend_parser.add_argument(
        "--outputs-root",
        type=Path,
        default=Path("outputs"),
        help="Research outputs root. Default: outputs.",
    )
    build_frontend_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Frontend output directory. Defaults to outputs/frontend/frontend_YYYYMMDD_HHMMSS.",
    )
    build_frontend_parser.add_argument(
        "--update-latest",
        action="store_true",
        help="Also sync the generated site to outputs/frontend/latest.",
    )
    build_frontend_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    build_frontend_parser.set_defaults(handler=_cmd_build_frontend)

    serve_frontend_parser = subparsers.add_parser(
        "serve-frontend",
        help="Serve a generated read-only frontend directory with Python http.server.",
    )
    serve_frontend_parser.add_argument("--dir", type=Path, required=True, help="Generated frontend directory.")
    serve_frontend_parser.add_argument("--host", default="127.0.0.1", help="Host. Default: 127.0.0.1.")
    serve_frontend_parser.add_argument("--port", type=int, default=8765, help="Port. Default: 8765.")
    serve_frontend_parser.set_defaults(handler=_cmd_serve_frontend)

    import_data_parser = subparsers.add_parser("import-data", help="Import local CSV data into a versioned data directory.")
    import_data_parser.add_argument("--source-name", required=True, help="Data source name, such as local_csv.")
    import_data_parser.add_argument(
        "--source-data-dir",
        type=Path,
        required=True,
        help="Directory containing stock_master.csv, daily_bar.csv, financial_summary.csv, and announcement_event.csv.",
    )
    import_data_parser.add_argument(
        "--target-root-dir",
        type=Path,
        default=Path("data/imports"),
        help="Root directory for versioned imports. Default: data/imports.",
    )
    import_data_parser.add_argument("--data-version", default=None, help="Optional data version directory name.")
    import_data_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    import_data_parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing import version.")
    import_data_parser.add_argument(
        "--quality-report",
        action="store_true",
        help="Generate a data quality report after a successful import.",
    )
    import_data_parser.add_argument("--notes", default=None, help="Optional notes saved in import_manifest.json.")
    import_data_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    import_data_parser.set_defaults(handler=_cmd_import_data)

    list_imports_parser = subparsers.add_parser("list-imports", help="List versioned data imports.")
    list_imports_parser.add_argument(
        "--target-root-dir",
        type=Path,
        default=Path("data/imports"),
        help="Root directory for versioned imports. Default: data/imports.",
    )
    list_imports_parser.add_argument("--source-name", default=None, help="Optional source name filter.")
    list_imports_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    list_imports_parser.set_defaults(handler=_cmd_list_imports)

    inspect_import_parser = subparsers.add_parser("inspect-import", help="Inspect one versioned data import.")
    inspect_import_parser.add_argument("--source-name", required=True, help="Data source name.")
    inspect_import_parser.add_argument("--data-version", required=True, help="Data version.")
    inspect_import_parser.add_argument(
        "--target-root-dir",
        type=Path,
        default=Path("data/imports"),
        help="Root directory for versioned imports. Default: data/imports.",
    )
    inspect_import_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    inspect_import_parser.set_defaults(handler=_cmd_inspect_import)

    build_universe_parser = subparsers.add_parser("build-universe", help="Build daily research universe.")
    build_universe_parser.add_argument("--date", required=True, help="Trade date in YYYY-MM-DD format.")
    build_universe_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    build_universe_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    build_universe_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path. Defaults to outputs/universe/universe_daily_YYYY-MM-DD.csv.",
    )
    build_universe_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    build_universe_parser.set_defaults(handler=_cmd_build_universe)

    compute_factors_parser = subparsers.add_parser("compute-factors", help="Compute daily price and liquidity factors.")
    compute_factors_parser.add_argument("--date", required=True, help="Trade date in YYYY-MM-DD format.")
    compute_factors_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    compute_factors_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    compute_factors_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path. Defaults to outputs/factors/factor_daily_YYYY-MM-DD.csv.",
    )
    compute_factors_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    compute_factors_parser.set_defaults(handler=_cmd_compute_factors)

    compute_events_parser = subparsers.add_parser("compute-events", help="Compute daily announcement event factors.")
    compute_events_parser.add_argument("--date", required=True, help="Trade date in YYYY-MM-DD format.")
    compute_events_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    compute_events_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    compute_events_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path. Defaults to outputs/events/event_daily_YYYY-MM-DD.csv.",
    )
    compute_events_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    compute_events_parser.set_defaults(handler=_cmd_compute_events)

    generate_signals_parser = subparsers.add_parser("generate-signals", help="Generate daily research signals.")
    generate_signals_parser.add_argument("--date", required=True, help="Trade date in YYYY-MM-DD format.")
    generate_signals_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    generate_signals_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    generate_signals_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path. Defaults to outputs/signals/signal_daily_YYYY-MM-DD.csv.",
    )
    generate_signals_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    generate_signals_parser.set_defaults(handler=_cmd_generate_signals)

    run_backtest_parser = subparsers.add_parser("run-backtest", help="Run an offline research backtest.")
    run_backtest_parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format.")
    run_backtest_parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format.")
    run_backtest_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    run_backtest_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    run_backtest_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/backtests/backtest_START_END/.",
    )
    run_backtest_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    run_backtest_parser.add_argument(
        "--record-experiment",
        action="store_true",
        help="Record this completed backtest in the experiment registry.",
    )
    run_backtest_parser.add_argument("--experiment-tag", action="append", default=[], help="Experiment tag. Can be repeated.")
    run_backtest_parser.add_argument("--experiment-notes", default=None, help="Optional experiment notes.")
    run_backtest_parser.add_argument(
        "--experiment-registry-dir",
        type=Path,
        default=Path("outputs/experiments"),
        help="Experiment registry directory. Default: outputs/experiments.",
    )
    run_backtest_parser.set_defaults(handler=_cmd_run_backtest)

    daily_report_parser = subparsers.add_parser("daily-report", help="Generate a daily research report.")
    daily_report_parser.add_argument("--date", required=True, help="Report date in YYYY-MM-DD format.")
    daily_report_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    daily_report_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    daily_report_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/reports/daily_YYYY-MM-DD/.",
    )
    daily_report_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    daily_report_parser.set_defaults(handler=_cmd_daily_report)

    backtest_report_parser = subparsers.add_parser("backtest-report", help="Generate a backtest research report.")
    backtest_report_parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format.")
    backtest_report_parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format.")
    backtest_report_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    backtest_report_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    backtest_report_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/reports/backtest_START_END/.",
    )
    backtest_report_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    backtest_report_parser.add_argument(
        "--reuse-backtest-dir",
        type=Path,
        default=None,
        help="Read metrics.json, trades.csv, and daily_equity.csv from an existing backtest output directory.",
    )
    backtest_report_parser.set_defaults(handler=_cmd_backtest_report)

    train_probability_parser = subparsers.add_parser(
        "train-probability-model",
        help="Train the baseline research probability model.",
    )
    train_probability_parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD format.")
    train_probability_parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD format.")
    train_probability_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    train_probability_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    train_probability_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/models/probability_START_END/.",
    )
    train_probability_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    train_probability_parser.set_defaults(handler=_cmd_train_probability_model)

    predict_probability_parser = subparsers.add_parser(
        "predict-probabilities",
        help="Predict daily research probabilities from a trained model.",
    )
    predict_probability_parser.add_argument("--date", required=True, help="Prediction date in YYYY-MM-DD format.")
    predict_probability_parser.add_argument(
        "--model-dir",
        type=Path,
        required=True,
        help="Directory containing model.json.",
    )
    predict_probability_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    predict_probability_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    predict_probability_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="CSV output path. Defaults to outputs/probability/probability_daily_YYYY-MM-DD.csv.",
    )
    predict_probability_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    predict_probability_parser.set_defaults(handler=_cmd_predict_probabilities)

    audit_leakage_parser = subparsers.add_parser("audit-leakage", help="Run point-in-time leakage audit.")
    audit_leakage_parser.add_argument("--date", default=None, help="Audit one date in YYYY-MM-DD format.")
    audit_leakage_parser.add_argument("--start", default=None, help="Audit range start date in YYYY-MM-DD format.")
    audit_leakage_parser.add_argument("--end", default=None, help="Audit range end date in YYYY-MM-DD format.")
    audit_leakage_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    audit_leakage_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    audit_leakage_parser.add_argument("--source-name", default="local_csv", help="Data source name for audit metadata.")
    audit_leakage_parser.add_argument("--data-version", default="sample", help="Data version or import batch id.")
    audit_leakage_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/audit/leakage_DATE or leakage_START_END.",
    )
    audit_leakage_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    audit_leakage_parser.set_defaults(handler=_cmd_audit_leakage)

    quality_report_parser = subparsers.add_parser("quality-report", help="Generate a local CSV data quality report.")
    quality_report_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    quality_report_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    quality_report_parser.add_argument("--source-name", default=None, help="Optional data source name.")
    quality_report_parser.add_argument("--data-version", default=None, help="Optional data version.")
    quality_report_parser.add_argument("--date", default=None, help="Optional target research date in YYYY-MM-DD format.")
    quality_report_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/quality/quality_YYYYMMDD_HHMMSS.",
    )
    quality_report_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    quality_report_parser.set_defaults(handler=_cmd_quality_report)

    check_security_parser = subparsers.add_parser("check-security", help="Scan configuration for unsafe secrets and trading flags.")
    check_security_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    check_security_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/security/security_YYYYMMDD_HHMMSS.",
    )
    check_security_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    check_security_parser.set_defaults(handler=_cmd_check_security)

    check_secrets_parser = subparsers.add_parser("check-secrets", help="Check configured secret environment variables.")
    check_secrets_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    check_secrets_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    check_secrets_parser.set_defaults(handler=_cmd_check_secrets)

    show_network_policy_parser = subparsers.add_parser("show-network-policy", help="Show offline/network safety policy.")
    show_network_policy_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    show_network_policy_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    show_network_policy_parser.set_defaults(handler=_cmd_show_network_policy)

    validate_adapter_contract_parser = subparsers.add_parser(
        "validate-adapter-contract",
        help="Validate an offline external adapter fixture contract.",
    )
    validate_adapter_contract_parser.add_argument("--source-name", required=True, help="External source name.")
    validate_adapter_contract_parser.add_argument(
        "--fixture-dir",
        type=Path,
        required=True,
        help="Directory containing the external source fixture CSV files.",
    )
    validate_adapter_contract_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/contracts/SOURCE_NAME.",
    )
    validate_adapter_contract_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    validate_adapter_contract_parser.set_defaults(handler=_cmd_validate_adapter_contract)

    convert_source_fixture_parser = subparsers.add_parser(
        "convert-source-fixture",
        help="Convert an offline external source fixture into normalized local CSV tables.",
    )
    convert_source_fixture_parser.add_argument("--source-name", required=True, help="External source name.")
    convert_source_fixture_parser.add_argument(
        "--fixture-dir",
        type=Path,
        required=True,
        help="Directory containing the external source fixture CSV files.",
    )
    convert_source_fixture_parser.add_argument(
        "--mapping-path",
        type=Path,
        default=None,
        help="Mapping YAML path. Defaults to configs/ashare_alpha/data_sources/SOURCE_NAME_mapping.yaml.",
    )
    convert_source_fixture_parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Output directory for stock_master.csv, daily_bar.csv, financial_summary.csv, and announcement_event.csv.",
    )
    convert_source_fixture_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    convert_source_fixture_parser.set_defaults(handler=_cmd_convert_source_fixture)

    materialize_source_parser = subparsers.add_parser(
        "materialize-source",
        help="Materialize an external source runtime profile into standard local CSV tables.",
    )
    materialize_source_parser.add_argument("--profile", type=Path, required=True, help="Source profile YAML path.")
    materialize_source_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    materialize_source_parser.add_argument(
        "--output-root-dir",
        type=Path,
        default=None,
        help="Output root directory. Defaults to profile output_root_dir.",
    )
    materialize_source_parser.add_argument("--data-version", default=None, help="Optional data version directory name.")
    materialize_source_parser.add_argument(
        "--quality-report",
        action="store_true",
        help="Generate a data quality report in the materialized output directory.",
    )
    materialize_source_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    materialize_source_parser.set_defaults(handler=_cmd_materialize_source)

    run_pipeline_parser = subparsers.add_parser("run-pipeline", help="Run the complete daily research pipeline.")
    run_pipeline_parser.add_argument("--date", required=True, help="Pipeline date in YYYY-MM-DD format.")
    run_pipeline_parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="Directory containing local CSV files. Defaults to data/sample/ashare_alpha/.",
    )
    run_pipeline_parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help="Directory containing ashare_alpha YAML configs. Defaults to configs/ashare_alpha/.",
    )
    run_pipeline_parser.add_argument(
        "--model-dir",
        type=Path,
        default=None,
        help="Optional probability model directory containing model.json.",
    )
    run_pipeline_parser.add_argument(
        "--require-probability",
        action="store_true",
        help="Fail the pipeline if probability prediction fails.",
    )
    run_pipeline_parser.add_argument(
        "--audit-leakage",
        action="store_true",
        help="Run point-in-time leakage audit after data validation.",
    )
    run_pipeline_parser.add_argument(
        "--quality-report",
        action="store_true",
        help="Run data quality report after data validation.",
    )
    run_pipeline_parser.add_argument(
        "--check-security",
        action="store_true",
        help="Run configuration security scan before data validation.",
    )
    run_pipeline_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to outputs/pipelines/pipeline_YYYY-MM-DD/.",
    )
    run_pipeline_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format. Default: text.",
    )
    run_pipeline_parser.add_argument(
        "--record-experiment",
        action="store_true",
        help="Record this completed pipeline in the experiment registry.",
    )
    run_pipeline_parser.add_argument("--experiment-tag", action="append", default=[], help="Experiment tag. Can be repeated.")
    run_pipeline_parser.add_argument("--experiment-notes", default=None, help="Optional experiment notes.")
    run_pipeline_parser.add_argument(
        "--experiment-registry-dir",
        type=Path,
        default=Path("outputs/experiments"),
        help="Experiment registry directory. Default: outputs/experiments.",
    )
    run_pipeline_parser.set_defaults(handler=_cmd_run_pipeline)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the minimal CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return args.handler(args)
    except (ConfigError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_show_version(args: argparse.Namespace) -> int:
    package_location = Path(ashare_alpha_package.__file__).resolve()
    payload = {
        "version": __version__,
        "package_location": str(package_location),
        "python_version": sys.version.split()[0],
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"version: {payload['version']}")
        print(f"package_location: {payload['package_location']}")
        print(f"python_version: {payload['python_version']}")
    return 0


def _cmd_release_check(args: argparse.Namespace) -> int:
    manifest = ReleaseChecker().run()
    output_dir = args.output_dir or Path("outputs") / "release" / f"v{manifest.version}"
    save_release_manifest_json(manifest, output_dir / "release_manifest.json")
    save_release_checklist_md(manifest, output_dir / "release_checklist.md")
    payload = {
        "version": manifest.version,
        "checks_passed": manifest.checks_passed,
        "pass_count": manifest.pass_count,
        "warn_count": manifest.warn_count,
        "fail_count": manifest.fail_count,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"version: {payload['version']}")
        print(f"checks_passed: {payload['checks_passed']}")
        print(f"PASS / WARN / FAIL: {payload['pass_count']} / {payload['warn_count']} / {payload['fail_count']}")
        print(f"output_dir: {output_dir}")
    return 1 if manifest.fail_count > 0 else 0


def _cmd_run_sweep(args: argparse.Namespace) -> int:
    result = SweepRunner(args.spec, output_dir=args.output_dir).run()
    payload = {
        "sweep_id": result.sweep_id,
        "sweep_name": result.sweep_name,
        "command": result.command,
        "total_variants": result.total_variants,
        "success_count": result.success_count,
        "partial_count": result.partial_count,
        "failed_count": result.failed_count,
        "output_dir": result.output_dir,
        "summary": result.summary,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Sweep run: {result.sweep_name}")
        print(f"Sweep id: {result.sweep_id}")
        print(f"Command: {result.command}")
        print(f"Total variants: {result.total_variants}")
        print(f"Success: {result.success_count}")
        print(f"Partial: {result.partial_count}")
        print(f"Failed: {result.failed_count}")
        if result.failed_count and result.success_count + result.partial_count > 0:
            print("部分 variant 失败，请查看 sweep_summary.md 和各 variant error_message。")
        print(f"Output: {result.output_dir}")
    return 1 if result.failed_count == result.total_variants else 0


def _cmd_show_sweep(args: argparse.Namespace) -> int:
    result = load_sweep_result_json(args.path)
    if args.format == "json":
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    print(f"Sweep: {result.sweep_name}")
    print(f"Sweep id: {result.sweep_id}")
    print(f"Command: {result.command}")
    print(f"Total variants: {result.total_variants}")
    print(f"Success / Partial / Failed: {result.success_count} / {result.partial_count} / {result.failed_count}")
    print(f"Output: {result.output_dir}")
    rows = build_metrics_table(result)
    for row in rows:
        metrics = {key: value for key, value in row.items() if key not in _SWEEP_BASE_ROW_KEYS and value not in {"", None}}
        print(f"- {row['variant_name']}: {row['status']}")
        print(f"  experiment_id: {row.get('experiment_id') or '-'}")
        print(f"  output_dir: {row['output_dir']}")
        if metrics:
            print(f"  metrics: {json.dumps(metrics, ensure_ascii=False)}")
    return 0


def _cmd_run_walkforward(args: argparse.Namespace) -> int:
    result = WalkForwardRunner(args.spec, output_dir=args.output_dir).run()
    payload = {
        "walkforward_id": result.walkforward_id,
        "name": result.name,
        "command": result.command,
        "fold_count": result.fold_count,
        "success_count": result.success_count,
        "failed_count": result.failed_count,
        "skipped_count": result.skipped_count,
        "positive_return_ratio": result.stability_metrics.get("positive_return_ratio"),
        "mean_total_return": result.stability_metrics.get("mean_total_return"),
        "worst_max_drawdown": result.stability_metrics.get("worst_max_drawdown"),
        "output_dir": str(Path(args.output_dir or _walkforward_default_output_root(args.spec)) / result.walkforward_id),
        "summary": result.summary,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Walk-forward run: {result.name}")
        print(f"Walk-forward id: {result.walkforward_id}")
        print(f"Command: {result.command}")
        print(f"Fold count: {result.fold_count}")
        print(f"Success: {result.success_count}")
        print(f"Failed: {result.failed_count}")
        print(f"Skipped: {result.skipped_count}")
        print(f"Positive return ratio: {_format_optional(payload['positive_return_ratio'])}")
        print(f"Mean total return: {_format_optional(payload['mean_total_return'])}")
        print(f"Worst max drawdown: {_format_optional(payload['worst_max_drawdown'])}")
        if result.failed_count and result.success_count + result.skipped_count > 0:
            print("部分 fold 失败，请查看 walkforward_summary.md 和各 fold error_message。")
        print(f"Output: {payload['output_dir']}")
    return 1 if result.fold_count > 0 and result.failed_count == result.fold_count else 0


def _cmd_show_walkforward(args: argparse.Namespace) -> int:
    result = load_walkforward_result_json(args.path)
    if args.format == "json":
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    print(f"Walk-forward: {result.name}")
    print(f"Walk-forward id: {result.walkforward_id}")
    print(f"Command: {result.command}")
    print(f"Fold count: {result.fold_count}")
    print(f"Success / Failed / Skipped: {result.success_count} / {result.failed_count} / {result.skipped_count}")
    for fold in result.folds:
        print(f"- fold_{fold.fold_index:03d}: {fold.status} {fold.test_start.isoformat()}..{fold.test_end.isoformat()}")
        print(f"  experiment_id: {fold.experiment_id or '-'}")
        print(f"  output_dir: {fold.output_dir or '-'}")
        metrics = {
            key: fold.metrics.get(key)
            for key in ("total_return", "max_drawdown", "sharpe", "trade_count")
            if fold.metrics.get(key) is not None
        }
        if metrics:
            print(f"  metrics: {json.dumps(metrics, ensure_ascii=False)}")
        if fold.error_message:
            print(f"  error: {fold.error_message}")
    print("Stability metrics:")
    print(json.dumps(result.stability_metrics, ensure_ascii=False, indent=2))
    if result.overfit_warnings:
        print("Overfit warnings:")
        for warning in result.overfit_warnings:
            print(f"  - {warning}")
    return 0


def _cmd_select_candidates(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or Path("outputs") / "candidates" / f"selection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    report = CandidateSelector(rules_path=args.rules, sources=args.source).select()
    save_candidate_selection_report_json(report, output_dir / "candidate_selection.json")
    save_candidate_selection_report_md(report, output_dir / "candidate_selection.md")
    save_candidate_scores_csv(report, output_dir / "candidate_scores.csv")
    top_candidate = report.scores[0] if report.scores else None
    payload = {
        "selection_id": report.selection_id,
        "total_candidates": report.total_candidates,
        "advance_count": report.advance_count,
        "review_count": report.review_count,
        "reject_count": report.reject_count,
        "top_candidate": top_candidate.model_dump(mode="json") if top_candidate else None,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Candidate selection completed")
        print(f"Selection id: {payload['selection_id']}")
        print(f"Total candidates: {payload['total_candidates']}")
        print(f"Advance: {payload['advance_count']}")
        print(f"Review: {payload['review_count']}")
        print(f"Reject: {payload['reject_count']}")
        if top_candidate:
            print(f"Top candidate: {top_candidate.candidate_id} ({top_candidate.total_score:.2f}, {top_candidate.recommendation})")
        print(f"Output: {output_dir}")
        print("Research screening only; not investment advice, not a guarantee of future returns, and no orders are placed.")
    return 1 if report.total_candidates == 0 else 0


def _cmd_promote_candidate_config(args: argparse.Namespace) -> int:
    report = load_candidate_selection_report_json(args.selection)
    candidate = next((item for item in report.candidates if item.candidate_id == args.candidate_id), None)
    if candidate is None:
        raise ValueError(f"candidate-id not found in selection: {args.candidate_id}")
    result = promote_candidate_config(
        candidate=candidate,
        promoted_name=args.promoted_name,
        target_root=args.target_root,
        allow_overwrite=args.overwrite,
    )
    payload = {
        "status": result.status,
        "candidate_id": result.candidate_id,
        "target_config_dir": result.target_config_dir,
        "message": result.message,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Status: {result.status}")
        print(f"Candidate id: {result.candidate_id}")
        print(f"Target config dir: {result.target_config_dir}")
        print(f"Message: {result.message}")
    return 0 if result.status == "SUCCESS" else 1


def _cmd_build_dashboard(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or Path("outputs") / "dashboard" / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    index = DashboardScanner(args.outputs_root).scan()
    summary = build_dashboard_summary(index)
    save_dashboard_index_json(index, output_dir / "dashboard_index.json")
    save_dashboard_summary_json(summary, output_dir / "dashboard_summary.json")
    save_dashboard_markdown(index, summary, output_dir / "dashboard.md")
    save_dashboard_tables(index, summary, output_dir / "dashboard_tables")
    payload = {
        "artifact_count": index.artifact_count,
        "artifacts_by_type": index.artifacts_by_type,
        "warning_count": len(summary.warning_items),
        "output_dir": str(output_dir),
        "summary_text": summary.summary_text,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Research dashboard built")
        print(f"Artifact count: {payload['artifact_count']}")
        print(f"Artifacts by type: {json.dumps(payload['artifacts_by_type'], ensure_ascii=False)}")
        print(f"Warning count: {payload['warning_count']}")
        print(f"Output: {output_dir}")
        if index.artifact_count == 0:
            print("未发现研究产物。")
    return 0


def _cmd_show_dashboard(args: argparse.Namespace) -> int:
    index, summary = _load_dashboard_paths(args.path)
    latest = {
        "pipeline": _dashboard_artifact_brief(summary.latest_pipeline),
        "backtest": _dashboard_artifact_brief(summary.latest_backtest),
        "sweep": _dashboard_artifact_brief(summary.latest_sweep),
        "walkforward": _dashboard_artifact_brief(summary.latest_walkforward),
        "candidate_selection": _dashboard_artifact_brief(summary.latest_candidate_selection),
    }
    payload = {
        "artifact_count": index.artifact_count if index else None,
        "artifacts_by_type": index.artifacts_by_type if index else {},
        "latest": latest,
        "warning_items": summary.warning_items,
        "summary_text": summary.summary_text,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Research dashboard")
        print(f"Artifact count: {payload['artifact_count']}")
        print(f"Artifacts by type: {json.dumps(payload['artifacts_by_type'], ensure_ascii=False)}")
        print("Latest:")
        for key, value in latest.items():
            print(f"  {key}: {value.get('name') if value else '-'}")
        print(f"Warnings: {len(summary.warning_items)}")
        for item in summary.warning_items:
            print(f"  - [{item.get('artifact_type')}] {item.get('name')}: {item.get('message')}")
        print(summary.summary_text)
    return 0


def _cmd_build_frontend(args: argparse.Namespace) -> int:
    output_dir = args.output_dir or Path("outputs") / "frontend" / f"frontend_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    data = collect_frontend_data(args.outputs_root)
    latest_dir = args.outputs_root / "frontend" / "latest"
    save_frontend_site(data, output_dir, update_latest=args.update_latest, latest_dir=latest_dir)
    payload = {
        "artifact_count": data.summary.get("artifact_count", 0),
        "warning_count": len(data.warning_items),
        "output_dir": str(output_dir),
        "latest_dir": str(latest_dir) if args.update_latest else None,
        "index_html": str(output_dir / "index.html"),
        "frontend_data_json": str(output_dir / "frontend_data.json"),
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Research frontend built")
        print(f"Artifact count: {payload['artifact_count']}")
        print(f"Warning count: {payload['warning_count']}")
        print(f"Output: {output_dir}")
        if args.update_latest:
            print(f"Latest: {latest_dir}")
        print("Static files: index.html, assets/app.js, assets/style.css, frontend_data.json")
    return 0


def _cmd_serve_frontend(args: argparse.Namespace) -> int:
    warning = host_warning(args.host)
    if warning:
        print(warning, file=sys.stderr)
    serve_frontend(args.dir, host=args.host, port=args.port)
    return 0


def _load_dashboard_paths(path: Path):
    if not path.exists():
        raise ValueError(f"dashboard path does not exist: {path}")
    if path.is_dir():
        index_path = path / "dashboard_index.json"
        summary_path = path / "dashboard_summary.json"
    elif path.name == "dashboard_index.json":
        index_path = path
        summary_path = path.parent / "dashboard_summary.json"
    elif path.name == "dashboard_summary.json":
        summary_path = path
        index_path = path.parent / "dashboard_index.json"
    else:
        raise ValueError("path must be a dashboard directory, dashboard_index.json, or dashboard_summary.json")
    if not summary_path.exists():
        raise ValueError(f"dashboard_summary.json does not exist: {summary_path}")
    summary = load_dashboard_summary_json(summary_path)
    if index_path.exists():
        index = load_dashboard_index_json(index_path)
    else:
        index = None
    return index, summary


def _dashboard_artifact_brief(artifact) -> dict[str, object] | None:
    if artifact is None:
        return None
    return {
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "name": artifact.name,
        "status": artifact.status,
        "path": artifact.path,
    }


def _cmd_show_config(args: argparse.Namespace) -> int:
    config = load_project_config(args.config_dir)
    print(json.dumps(redact_mapping(config.model_dump(mode="json")), ensure_ascii=False, indent=2))
    return 0


def _cmd_validate_data(args: argparse.Namespace) -> int:
    report = LocalCsvAdapter(args.data_dir).validate_all()
    payload = report.model_dump(mode="json")

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        status = "passed" if report.passed else "failed"
        print(f"Data validation {status}: {args.data_dir}")
        print("Row counts:")
        for table_name, row_count in sorted(report.row_counts.items()):
            print(f"  {table_name}: {row_count}")
        if report.warnings:
            print("Warnings:")
            for warning in report.warnings:
                print(f"  - {warning}")
        if report.errors:
            print("Errors:")
            for error in report.errors:
                print(f"  - {error}")

    return 0 if report.passed else 1


def _cmd_list_data_sources(args: argparse.Namespace) -> int:
    sources = get_default_data_source_registry().list_sources()
    security_config = load_project_config(_default_config_dir()).security
    payload = [_data_source_summary(source, security_config) for source in sources]
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Registered data sources:")
        for source in payload:
            print(
                f"- {source['name']} | {source['display_name']} | status={source['status']} | "
                f"stock_master={source['supports_stock_master']} | daily_bar={source['supports_daily_bar']} | "
                f"network={source['requires_network']} | api_key={source['requires_api_key']} | "
                f"live_trading={source['is_live_trading_source']} | "
                f"security_enabled={source['security_enabled']} | "
                f"security_api_key_env_var={source['security_api_key_env_var']}"
            )
    return 0


def _cmd_inspect_data_source(args: argparse.Namespace) -> int:
    source = get_default_data_source_registry().get_source(args.name)
    security_config = load_project_config(_default_config_dir()).security
    security_summary = _data_source_security_summary(source.name, security_config)
    payload = source.model_dump(mode="json")
    payload["security"] = security_summary
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Data source: {source.name}")
        print(f"Display name: {source.display_name}")
        print(f"Status: {source.status}")
        print(f"Adapter class: {source.adapter_class}")
        print(f"Description: {source.description}")
        if source.status == "stub":
            print("Status note: 仅占位，不会联网。")
        print("Capabilities:")
        for key, value in source.capabilities.model_dump(mode="json").items():
            print(f"  {key}: {value}")
        print("Security:")
        for key, value in security_summary.items():
            print(f"  {key}: {value}")
    return 0


def _cmd_list_source_profiles(args: argparse.Namespace) -> int:
    profiles = [_load_source_profile(path) for path in sorted(args.profiles_dir.glob("*.yaml"))]
    payload = [_source_profile_summary(profile) for profile in profiles]
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Source runtime profiles:")
        for profile in payload:
            print(
                f"- {profile['source_name']} | {profile['display_name']} | mode={profile['mode']} | "
                f"enabled={profile['enabled']} | network={profile['requires_network']} | "
                f"api_key={profile['requires_api_key']} | fixture_dir={profile['fixture_dir']} | "
                f"cache_dir={profile['cache_dir']}"
            )
    return 0


def _cmd_inspect_source_profile(args: argparse.Namespace) -> int:
    config_dir = args.config_dir or _default_config_dir()
    profile = _load_source_profile(args.profile)
    security = load_project_config(config_dir).security
    can_run, reason = _can_profile_run_offline(profile, security)
    payload = profile.model_dump(mode="json")
    payload["security"] = _source_runtime_security_summary(security)
    payload["can_run_offline"] = can_run
    payload["offline_reason"] = reason
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Source profile: {profile.source_name}")
        for key, value in profile.model_dump(mode="json").items():
            print(f"{key}: {value}")
        print("Security:")
        for key, value in payload["security"].items():
            print(f"  {key}: {value}")
        print(f"Can run offline: {can_run}")
        if reason:
            print(f"Reason: {reason}")
    return 0 if can_run else 1


def _cmd_record_experiment(args: argparse.Namespace) -> int:
    config_dir = args.config_dir or _default_config_dir()
    record = ExperimentRecorder(ExperimentRegistry(args.registry_dir)).record_completed_run(
        command=args.command,
        command_args={"command": args.command},
        status=args.status,
        output_dir=args.output_dir,
        data_dir=args.data_dir,
        config_dir=config_dir,
        notes=args.notes,
        tags=args.tag,
    )
    summary = _experiment_record_summary(record, args.registry_dir)
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Experiment recorded")
        print(f"Experiment id: {summary['experiment_id']}")
        print(f"Command: {summary['command']}")
        print(f"Status: {summary['status']}")
        print(f"Metrics: {summary['metrics_count']}")
        print(f"Artifacts: {summary['artifacts_count']}")
        print(f"Registry: {summary['registry_dir']}")
    return 0


def _cmd_list_experiments(args: argparse.Namespace) -> int:
    registry = ExperimentRegistry(args.registry_dir)
    records = registry.list()
    if args.command:
        records = [record for record in records if record.command == args.command]
    if args.tag:
        records = [record for record in records if args.tag in record.tags]
    payload = [_experiment_list_row(record) for record in records]
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Experiments:")
        for row in payload:
            print(
                f"- {row['experiment_id']} | {row['created_at']} | {row['command']} | {row['status']} | "
                f"data={row['data_source']}/{row['data_version']} | config={row['config_hash_short']} | "
                f"metrics={row['metrics_count']} | artifacts={row['artifacts_count']} | tags={','.join(row['tags'])}"
            )
    return 0


def _cmd_show_experiment(args: argparse.Namespace) -> int:
    record = ExperimentRegistry(args.registry_dir).get(args.id)
    payload = record.model_dump(mode="json")
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Experiment: {record.experiment_id}")
        print(f"Created at: {record.created_at.isoformat()}")
        print(f"Command: {record.command}")
        print(f"Status: {record.status}")
        print(f"Data: {record.data_source or '-'}/{record.data_version or '-'}")
        print(f"Config hash: {record.config_hash or '-'}")
        print(f"Output dir: {record.output_dir or '-'}")
        print(f"Notes: {record.notes or '-'}")
        print(f"Tags: {', '.join(record.tags) if record.tags else '-'}")
        print("Metrics:")
        for metric in record.metrics:
            print(f"  - {metric.name}: {metric.value} ({metric.category or '-'})")
        print("Artifacts:")
        for artifact in record.artifacts:
            print(f"  - {artifact.name} [{artifact.artifact_type}]: {artifact.path}")
    return 0


def _cmd_compare_experiments(args: argparse.Namespace) -> int:
    registry = ExperimentRegistry(args.registry_dir)
    baseline = registry.get(args.baseline)
    target = registry.get(args.target)
    result = compare_experiments(baseline, target)
    output_dir = args.output_dir or args.registry_dir / "comparisons"
    base_name = f"compare_{baseline.experiment_id}_{target.experiment_id}"
    save_compare_result_json(result, output_dir / f"{base_name}.json")
    save_compare_result_md(result, output_dir / f"{base_name}.md")
    summary = {
        "baseline": baseline.experiment_id,
        "target": target.experiment_id,
        "metric_count": len(result.metric_diffs),
        "output_dir": str(output_dir),
        "summary": result.summary,
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Experiment comparison generated")
        print(f"Baseline: {summary['baseline']}")
        print(f"Target: {summary['target']}")
        print(f"Metrics: {summary['metric_count']}")
        print(f"Output: {summary['output_dir']}")
        print(f"Summary: {summary['summary']}")
    return 0


def _cmd_import_data(args: argparse.Namespace) -> int:
    config_dir = args.config_dir or _default_config_dir()
    manifest = ImportJob(
        source_name=args.source_name,
        source_data_dir=args.source_data_dir,
        target_root_dir=args.target_root_dir,
        data_version=args.data_version,
        config_dir=config_dir,
        overwrite=args.overwrite,
        notes=args.notes,
        quality_report=args.quality_report,
    ).run()
    manifest_path = Path(manifest.target_data_dir) / "import_manifest.json"
    summary = {
        "status": manifest.status,
        "source_name": manifest.source_name,
        "data_version": manifest.data_version,
        "target_data_dir": manifest.target_data_dir,
        "validation_passed": manifest.validation_passed,
        "row_counts": manifest.row_counts,
        "import_manifest_path": str(manifest_path),
        "data_snapshot_path": manifest.snapshot_path,
        "error_message": manifest.error_message,
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Data import completed")
        print(f"Status: {summary['status']}")
        print(f"Source name: {summary['source_name']}")
        print(f"Data version: {summary['data_version']}")
        print(f"Target data dir: {summary['target_data_dir']}")
        print(f"Validation passed: {summary['validation_passed']}")
        print("Row counts:")
        for table_name, row_count in sorted(manifest.row_counts.items()):
            print(f"  {table_name}: {row_count}")
        print(f"Import manifest: {manifest_path}")
        if manifest.snapshot_path:
            print(f"Data snapshot: {manifest.snapshot_path}")
        if manifest.error_message:
            print(f"Error: {manifest.error_message}")
    return 0 if manifest.status == "SUCCESS" else 1


def _cmd_quality_report(args: argparse.Namespace) -> int:
    target_date = _parse_date(args.date) if args.date is not None else None
    config_dir = args.config_dir or _default_config_dir()
    report = DataQualityReporter(
        data_dir=args.data_dir,
        config_dir=config_dir,
        source_name=args.source_name,
        data_version=args.data_version,
        target_date=target_date,
    ).run()
    output_dir = args.output_dir or Path("outputs") / "quality" / f"quality_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    save_quality_report_json(report, output_dir / "quality_report.json")
    save_quality_report_md(report, output_dir / "quality_report.md")
    save_quality_issues_csv(report, output_dir / "quality_issues.csv")
    summary = {
        "passed": report.passed,
        "total_issues": report.total_issues,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "info_count": report.info_count,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Data quality report generated")
        print(f"Passed: {summary['passed']}")
        print(f"Total issues: {summary['total_issues']}")
        print(f"Errors: {summary['error_count']}")
        print(f"Warnings: {summary['warning_count']}")
        print(f"Info: {summary['info_count']}")
        print(f"Output: {output_dir}")
    return 1 if report.error_count > 0 else 0


def _cmd_check_security(args: argparse.Namespace) -> int:
    config_dir = args.config_dir or _default_config_dir()
    load_project_config(config_dir)
    report = ConfigSecurityScanner(config_dir).scan()
    output_dir = args.output_dir or Path("outputs") / "security" / f"security_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    save_security_scan_report_json(report, output_dir / "security_scan_report.json")
    save_security_scan_report_md(report, output_dir / "security_scan_report.md")
    summary = {
        "passed": report.passed,
        "total_issues": report.total_issues,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Security scan completed")
        print(f"Passed: {summary['passed']}")
        print(f"Total issues: {summary['total_issues']}")
        print(f"Errors: {summary['error_count']}")
        print(f"Warnings: {summary['warning_count']}")
        print(f"Output: {output_dir}")
    return 1 if report.error_count > 0 else 0


def _cmd_check_secrets(args: argparse.Namespace) -> int:
    config = load_project_config(args.config_dir or _default_config_dir())
    rows = []
    missing_enabled = False
    for source_name, source_config in sorted(config.security.data_sources.items()):
        env_var = source_config.api_key_env_var
        status = safe_env_status(env_var) if env_var else {"env_var_name": None, "is_set": False, "redacted_value": None}
        required_now = source_config.enabled and source_config.requires_api_key
        if required_now and not status["is_set"]:
            missing_enabled = True
        rows.append(
            {
                "source_name": source_name,
                "enabled": source_config.enabled,
                "requires_api_key": source_config.requires_api_key,
                "api_key_env_var": env_var,
                "is_set": status["is_set"],
                "redacted_value": status["redacted_value"],
                "status": "required" if required_now else "not required while disabled"
                if source_config.requires_api_key
                else "not required",
            }
        )
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print("Secret environment status:")
        for row in rows:
            print(
                f"- {row['source_name']} | enabled={row['enabled']} | "
                f"requires_api_key={row['requires_api_key']} | api_key_env_var={row['api_key_env_var']} | "
                f"is_set={row['is_set']} | redacted_value={row['redacted_value']} | status={row['status']}"
            )
    return 1 if missing_enabled else 0


def _cmd_show_network_policy(args: argparse.Namespace) -> int:
    security = load_project_config(args.config_dir or _default_config_dir()).security
    enabled_sources = sorted(name for name, source in security.data_sources.items() if source.enabled)
    network_sources = sorted(name for name, source in security.data_sources.items() if source.requires_network)
    payload = {
        "offline_mode": security.offline_mode,
        "allow_network": security.allow_network,
        "allow_broker_connections": security.allow_broker_connections,
        "allow_live_trading": security.allow_live_trading,
        "allowed_domains": security.network_policy.allowed_domains,
        "default_timeout_seconds": security.network_policy.default_timeout_seconds,
        "max_retries": security.network_policy.max_retries,
        "enabled_data_sources": enabled_sources,
        "network_required_data_sources": network_sources,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Network policy:")
        for key, value in payload.items():
            print(f"{key}: {value}")
    return 0


def _cmd_validate_adapter_contract(args: argparse.Namespace) -> int:
    source_name = args.source_name.strip().lower()
    output_dir = args.output_dir or Path("outputs") / "contracts" / source_name
    report = ExternalContractValidator(source_name=source_name, fixture_dir=args.fixture_dir).validate()
    save_contract_report_json(report, output_dir / "contract_report.json")
    save_contract_report_md(report, output_dir / "contract_report.md")
    summary = {
        "source_name": report.source_name,
        "passed": report.passed,
        "total_issues": report.total_issues,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Adapter contract validation completed")
        print(f"Source name: {summary['source_name']}")
        print(f"Passed: {summary['passed']}")
        print(f"Total issues: {summary['total_issues']}")
        print(f"Errors: {summary['error_count']}")
        print(f"Warnings: {summary['warning_count']}")
        print(f"Output: {output_dir}")
    return 1 if report.error_count > 0 else 0


def _cmd_convert_source_fixture(args: argparse.Namespace) -> int:
    source_name = args.source_name.strip().lower()
    output_dir = args.output_dir
    contract_report = ExternalContractValidator(source_name=source_name, fixture_dir=args.fixture_dir).validate()
    if not contract_report.passed:
        summary = {
            "source_name": contract_report.source_name,
            "passed": contract_report.passed,
            "total_issues": contract_report.total_issues,
            "error_count": contract_report.error_count,
            "warning_count": contract_report.warning_count,
            "fixture_dir": str(args.fixture_dir),
        }
        if args.format == "json":
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print("Adapter contract validation failed; conversion skipped")
            print(f"Source name: {summary['source_name']}")
            print(f"Errors: {summary['error_count']}")
            for issue in contract_report.issues:
                if issue.severity == "error":
                    print(f"  - {issue.dataset_name}: {issue.message}")
        return 1

    mapping_path = args.mapping_path or _default_mapping_path(source_name)
    result = ExternalFixtureConverter(
        source_name=source_name,
        fixture_dir=args.fixture_dir,
        mapping_path=mapping_path,
        output_dir=output_dir,
    ).convert()
    save_conversion_result_json(result, output_dir / "conversion_result.json")
    summary = {
        "source_name": result.source_name,
        "validation_passed": result.validation_passed,
        "generated_files": result.generated_files,
        "row_counts": result.row_counts,
        "output_dir": result.output_dir,
        "validation_errors": result.validation_errors,
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Source fixture conversion completed")
        print(f"Source name: {summary['source_name']}")
        print(f"Validation passed: {summary['validation_passed']}")
        print("Generated files:")
        for generated_file in result.generated_files:
            print(f"  - {generated_file}")
        print("Row counts:")
        for table_name, row_count in sorted(result.row_counts.items()):
            print(f"  {table_name}: {row_count}")
        print(f"Output: {output_dir}")
        if result.validation_errors:
            print("Validation errors:")
            for error in result.validation_errors:
                print(f"  - {error}")
    return 0 if result.validation_passed else 1


def _cmd_materialize_source(args: argparse.Namespace) -> int:
    config_dir = args.config_dir or _default_config_dir()
    result = SourceMaterializer(
        profile_path=args.profile,
        config_dir=config_dir,
        output_root_dir=args.output_root_dir,
        data_version=args.data_version,
        run_quality_report=args.quality_report,
    ).run()
    summary = {
        "status": result.status,
        "source_name": result.source_name,
        "mode": result.mode,
        "data_version": result.data_version,
        "output_dir": result.output_dir,
        "validation_passed": result.validation_passed,
        "quality_passed": result.quality_passed,
        "row_counts": result.row_counts,
        "error_message": result.error_message,
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Source materialization completed")
        print(f"Status: {summary['status']}")
        print(f"Source name: {summary['source_name']}")
        print(f"Mode: {summary['mode']}")
        print(f"Data version: {summary['data_version']}")
        print(f"Output dir: {summary['output_dir']}")
        print(f"Validation passed: {summary['validation_passed']}")
        print(f"Quality passed: {summary['quality_passed']}")
        print("Row counts:")
        for table_name, row_count in sorted(result.row_counts.items()):
            print(f"  {table_name}: {row_count}")
        if result.error_message:
            print(f"Error: {result.error_message}")
    return 0 if result.status == "SUCCESS" else 1


def _cmd_list_imports(args: argparse.Namespace) -> int:
    manifests = _scan_import_manifests(args.target_root_dir, args.source_name)
    payload = [_import_summary(manifest) for manifest in manifests]
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("Versioned data imports:")
        if not payload:
            print("(none)")
        for item in payload:
            print(
                f"- {item['source_name']} | {item['data_version']} | status={item['status']} | "
                f"validation={item['validation_passed']} | target={item['target_data_dir']}"
            )
    return 0


def _cmd_inspect_import(args: argparse.Namespace) -> int:
    source_name = normalize_source_name(args.source_name)
    validate_data_version(args.data_version)
    manifest_path = args.target_root_dir / source_name / args.data_version / "import_manifest.json"
    manifest = load_import_manifest(manifest_path)
    snapshot_payload = None
    if manifest.snapshot_path and Path(manifest.snapshot_path).exists():
        snapshot = json.loads(Path(manifest.snapshot_path).read_text(encoding="utf-8"))
        snapshot_payload = {
            "snapshot_id": snapshot.get("snapshot_id"),
            "source_name": snapshot.get("source_name"),
            "data_version": snapshot.get("data_version"),
            "row_counts": snapshot.get("row_counts"),
            "min_dates": snapshot.get("min_dates"),
            "max_dates": snapshot.get("max_dates"),
        }
    payload = {
        "manifest": manifest.model_dump(mode="json"),
        "copied_files": [item.model_dump(mode="json") for item in manifest.copied_files],
        "validation_summary": {
            "validation_passed": manifest.validation_passed,
            "validation_error_count": manifest.validation_error_count,
            "validation_warning_count": manifest.validation_warning_count,
            "row_counts": manifest.row_counts,
        },
        "snapshot_summary": snapshot_payload,
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Import: {manifest.source_name}/{manifest.data_version}")
        print(f"Status: {manifest.status}")
        print(f"Created at: {manifest.created_at.isoformat()}")
        print(f"Target data dir: {manifest.target_data_dir}")
        print(f"Validation passed: {manifest.validation_passed}")
        print("Copied files:")
        for item in manifest.copied_files:
            print(f"  - {item.dataset_name}: rows={item.rows}, sha256={item.sha256}")
        print("Row counts:")
        for table_name, row_count in sorted(manifest.row_counts.items()):
            print(f"  {table_name}: {row_count}")
        if snapshot_payload:
            print(f"Snapshot: {snapshot_payload['snapshot_id']}")
        if manifest.error_message:
            print(f"Error: {manifest.error_message}")
    return 0


def _cmd_build_universe(args: argparse.Namespace) -> int:
    trade_date = _parse_date(args.date)
    config = load_project_config(args.config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    builder = UniverseBuilder(
        config=config,
        stock_master=adapter.load_stock_master(),
        daily_bars=adapter.load_daily_bars(),
        financial_summary=adapter.load_financial_summary(),
        announcement_events=adapter.load_announcement_events(),
    )
    records = builder.build_for_date(trade_date)
    output_path = args.output or Path("outputs") / "universe" / f"universe_daily_{trade_date.isoformat()}.csv"
    save_universe_csv(records, output_path)
    summary = summarize_universe(records)
    summary["output"] = str(output_path)

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Universe built for {trade_date.isoformat()}")
        print(f"Total stocks: {summary['total']}")
        print(f"Allowed stocks: {summary['allowed']}")
        print(f"Excluded stocks: {summary['excluded']}")
        print("Exclude reason counts:")
        for reason, count in summary["reason_counts"].items():
            print(f"  {reason}: {count}")
        print(f"Output: {output_path}")
    return 0


def _cmd_compute_factors(args: argparse.Namespace) -> int:
    trade_date = _parse_date(args.date)
    config = load_project_config(args.config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    builder = FactorBuilder(
        config=config,
        daily_bars=adapter.load_daily_bars(),
        stock_master=adapter.load_stock_master(),
    )
    records = builder.build_for_date(trade_date)
    output_path = args.output or Path("outputs") / "factors" / f"factor_daily_{trade_date.isoformat()}.csv"
    save_factor_csv(records, output_path)
    summary = summarize_factors(records)
    summary["output"] = str(output_path)

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Factors computed for {trade_date.isoformat()}")
        print(f"Total stocks: {summary['total']}")
        print(f"Computable stocks: {summary['computable']}")
        print(f"Not computable stocks: {summary['not_computable']}")
        print("Missing reason counts:")
        for reason, count in summary["missing_reason_counts"].items():
            print(f"  {reason}: {count}")
        print(f"Output: {output_path}")
    return 0


def _cmd_compute_events(args: argparse.Namespace) -> int:
    trade_date = _parse_date(args.date)
    config = load_project_config(args.config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    builder = EventFeatureBuilder(
        config=config,
        announcement_events=adapter.load_announcement_events(),
        stock_master=adapter.load_stock_master(),
    )
    records = builder.build_for_date(trade_date)
    output_path = args.output or Path("outputs") / "events" / f"event_daily_{trade_date.isoformat()}.csv"
    save_event_daily_csv(records, output_path)
    summary = summarize_event_daily(records)
    summary["output"] = str(output_path)

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Events computed for {trade_date.isoformat()}")
        print(f"Total stocks: {summary['total']}")
        print(f"Stocks with events: {summary['with_events']}")
        print(f"Block-buy stocks: {summary['block_buy']}")
        print(f"Positive events: {summary['positive_events']}")
        print(f"Negative events: {summary['negative_events']}")
        print(f"High-risk events: {summary['high_risk_events']}")
        print(f"Output: {output_path}")
    return 0


def _cmd_generate_signals(args: argparse.Namespace) -> int:
    trade_date = _parse_date(args.date)
    config = load_project_config(args.config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    announcement_events = adapter.load_announcement_events()
    universe_records = UniverseBuilder(
        config=config,
        stock_master=stock_master,
        daily_bars=daily_bars,
        financial_summary=financial_summary,
        announcement_events=announcement_events,
    ).build_for_date(trade_date)
    factor_records = FactorBuilder(
        config=config,
        daily_bars=daily_bars,
        stock_master=stock_master,
    ).build_for_date(trade_date)
    event_records = EventFeatureBuilder(
        config=config,
        announcement_events=announcement_events,
        stock_master=stock_master,
    ).build_for_date(trade_date)
    records = SignalGenerator(
        config=config,
        stock_master=stock_master,
        financial_summary=financial_summary,
        universe_records=universe_records,
        factor_records=factor_records,
        event_records=event_records,
    ).generate_for_date(trade_date)
    output_path = args.output or Path("outputs") / "signals" / f"signal_daily_{trade_date.isoformat()}.csv"
    save_signal_csv(records, output_path)
    summary = summarize_signals(records)
    summary["output"] = str(output_path)

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Signals generated for {trade_date.isoformat()}")
        print(f"Total stocks: {summary['total']}")
        print(f"BUY: {summary['buy']}")
        print(f"WATCH: {summary['watch']}")
        print(f"BLOCK: {summary['block']}")
        print(f"High risk: {summary['high_risk']}")
        print(f"Market regime: {summary['market_regime']}")
        print(f"Output: {output_path}")
    return 0


def _cmd_run_backtest(args: argparse.Namespace) -> int:
    start_date = _parse_date(args.start)
    end_date = _parse_date(args.end)
    if start_date >= end_date:
        raise ValueError("start must be earlier than end")
    config_dir = args.config_dir or _default_config_dir()
    config = load_project_config(config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    result = BacktestEngine(
        config=config,
        stock_master=adapter.load_stock_master(),
        daily_bars=adapter.load_daily_bars(),
        financial_summary=adapter.load_financial_summary(),
        announcement_events=adapter.load_announcement_events(),
    ).run(start_date, end_date)
    output_dir = args.output_dir or Path("outputs") / "backtests" / f"backtest_{start_date.isoformat()}_{end_date.isoformat()}"
    save_trades_csv(result.trades, output_dir / "trades.csv")
    save_daily_equity_csv(result.daily_equity, output_dir / "daily_equity.csv")
    save_metrics_json(result.metrics, output_dir / "metrics.json")
    save_backtest_summary_md(result, output_dir / "summary.md")
    experiment_id = None
    if args.record_experiment:
        experiment = ExperimentRecorder(ExperimentRegistry(args.experiment_registry_dir)).record_completed_run(
            command="run-backtest",
            command_args={
                "start": args.start,
                "end": args.end,
                "data_dir": args.data_dir,
                "config_dir": config_dir,
                "output_dir": output_dir,
            },
            status="SUCCESS",
            output_dir=output_dir,
            data_dir=args.data_dir,
            config_dir=config_dir,
            notes=args.experiment_notes,
            tags=args.experiment_tag,
        )
        experiment_id = experiment.experiment_id
    summary = {
        "start_date": result.metrics.start_date.isoformat(),
        "end_date": result.metrics.end_date.isoformat(),
        "initial_cash": result.metrics.initial_cash,
        "final_equity": result.metrics.final_equity,
        "total_return": result.metrics.total_return,
        "max_drawdown": result.metrics.max_drawdown,
        "sharpe": result.metrics.sharpe,
        "trade_count": result.metrics.trade_count,
        "filled_trade_count": result.metrics.filled_trade_count,
        "rejected_trade_count": result.metrics.rejected_trade_count,
        "output_dir": str(output_dir),
        "experiment_id": experiment_id,
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Backtest run from {summary['start_date']} to {summary['end_date']}")
        print(f"Initial cash: {summary['initial_cash']:.2f}")
        print(f"Final equity: {summary['final_equity']:.2f}")
        print(f"Total return: {summary['total_return']:.2%}")
        print(f"Max drawdown: {summary['max_drawdown']:.2%}")
        print(f"Sharpe: {summary['sharpe']:.4f}")
        print(f"Trade count: {summary['trade_count']}")
        print(f"Filled trades: {summary['filled_trade_count']}")
        print(f"Rejected trades: {summary['rejected_trade_count']}")
        print(f"Output: {output_dir}")
        if experiment_id:
            print(f"Experiment id: {experiment_id}")
    return 0


def _cmd_daily_report(args: argparse.Namespace) -> int:
    report_date = _parse_date(args.date)
    config = load_project_config(args.config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    announcement_events = adapter.load_announcement_events()
    universe_records = UniverseBuilder(
        config=config,
        stock_master=stock_master,
        daily_bars=daily_bars,
        financial_summary=financial_summary,
        announcement_events=announcement_events,
    ).build_for_date(report_date)
    factor_records = FactorBuilder(config=config, daily_bars=daily_bars, stock_master=stock_master).build_for_date(
        report_date
    )
    event_records = EventFeatureBuilder(
        config=config,
        announcement_events=announcement_events,
        stock_master=stock_master,
    ).build_for_date(report_date)
    signal_records = SignalGenerator(
        config=config,
        stock_master=stock_master,
        financial_summary=financial_summary,
        universe_records=universe_records,
        factor_records=factor_records,
        event_records=event_records,
    ).generate_for_date(report_date)
    output_dir = args.output_dir or Path("outputs") / "reports" / f"daily_{report_date.isoformat()}"
    report = DailyReportBuilder(
        config=config,
        stock_master=stock_master,
        universe_records=universe_records,
        factor_records=factor_records,
        event_records=event_records,
        signal_records=signal_records,
        data_dir=args.data_dir,
        config_dir=args.config_dir or _default_config_dir(),
    ).build(report_date)
    save_daily_report(report, output_dir)
    summary = {
        "report_date": report.report_date.isoformat(),
        "market_regime": report.market_regime,
        "buy_count": report.buy_count,
        "watch_count": report.watch_count,
        "block_count": report.block_count,
        "high_risk_count": report.high_risk_count,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Daily report generated for {summary['report_date']}")
        print(f"Market regime: {summary['market_regime']}")
        print(f"BUY: {summary['buy_count']}")
        print(f"WATCH: {summary['watch_count']}")
        print(f"BLOCK: {summary['block_count']}")
        print(f"High risk: {summary['high_risk_count']}")
        print(f"Output: {output_dir}")
    return 0


def _cmd_backtest_report(args: argparse.Namespace) -> int:
    start_date = _parse_date(args.start)
    end_date = _parse_date(args.end)
    if start_date >= end_date:
        raise ValueError("start must be earlier than end")
    config = load_project_config(args.config_dir)
    output_dir = args.output_dir or Path("outputs") / "reports" / (
        f"backtest_{start_date.isoformat()}_{end_date.isoformat()}"
    )

    if args.reuse_backtest_dir is not None:
        result = _load_backtest_result(args.reuse_backtest_dir)
    else:
        adapter = LocalCsvAdapter(args.data_dir)
        validation_report = adapter.validate_all()
        if not validation_report.passed:
            _print_validation_failure(validation_report, args.format)
            return 1
        result = BacktestEngine(
            config=config,
            stock_master=adapter.load_stock_master(),
            daily_bars=adapter.load_daily_bars(),
            financial_summary=adapter.load_financial_summary(),
            announcement_events=adapter.load_announcement_events(),
        ).run(start_date, end_date)

    report = BacktestReportBuilder(result=result, config=config, output_dir=output_dir).build()
    save_backtest_report(report, output_dir)
    summary = {
        "start_date": report.start_date.isoformat(),
        "end_date": report.end_date.isoformat(),
        "total_return": report.total_return,
        "max_drawdown": report.max_drawdown,
        "sharpe": report.sharpe,
        "trade_count": report.trade_count,
        "no_trade": report.no_trade,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Backtest report generated from {summary['start_date']} to {summary['end_date']}")
        print(f"Total return: {summary['total_return']:.2%}")
        print(f"Max drawdown: {summary['max_drawdown']:.2%}")
        print(f"Sharpe: {summary['sharpe']:.4f}")
        print(f"Trade count: {summary['trade_count']}")
        print(f"No trade: {summary['no_trade']}")
        print(f"Output: {output_dir}")
    return 0


def _cmd_train_probability_model(args: argparse.Namespace) -> int:
    start_date = _parse_date(args.start)
    end_date = _parse_date(args.end)
    if start_date >= end_date:
        raise ValueError("start must be earlier than end")
    config = load_project_config(args.config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    trainer = ProbabilityTrainer(
        config=config,
        stock_master=adapter.load_stock_master(),
        daily_bars=adapter.load_daily_bars(),
        financial_summary=adapter.load_financial_summary(),
        announcement_events=adapter.load_announcement_events(),
    )
    result = trainer.train(start_date, end_date)
    output_dir = args.output_dir or Path("outputs") / "models" / (
        f"probability_{start_date.isoformat()}_{end_date.isoformat()}"
    )
    if config.probability.output.save_dataset:
        save_probability_dataset_csv(trainer.last_dataset, output_dir / "probability_dataset.csv")
    if config.probability.output.save_model:
        save_probability_model_json(result.model, output_dir / "model.json")
    if config.probability.output.save_metrics:
        save_probability_metrics_json(result.metrics, output_dir / "metrics.json")
    if config.probability.output.save_test_predictions:
        save_probability_predictions_csv(trainer.last_test_predictions, output_dir / "test_predictions.csv")
    save_probability_summary_md(result, output_dir / "summary.md")

    summary = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "dataset_rows": result.dataset_rows,
        "train_rows": result.train_rows,
        "test_rows": result.test_rows,
        "horizons": list(config.probability.horizons),
        "metrics": [metric.model_dump(mode="json") for metric in result.metrics],
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Probability model trained from {summary['start_date']} to {summary['end_date']}")
        print(f"Dataset rows: {summary['dataset_rows']}")
        print(f"Train rows: {summary['train_rows']}")
        print(f"Test rows: {summary['test_rows']}")
        print(f"Horizons: {', '.join(str(item) for item in summary['horizons'])}")
        for metric in result.metrics:
            print(
                f"  {metric.horizon}d: sample_count={metric.sample_count}, "
                f"actual_win_rate={_format_optional(metric.actual_win_rate)}, "
                f"accuracy={_format_optional(metric.accuracy)}, "
                f"auc={_format_optional(metric.auc)}, "
                f"brier_score={_format_optional(metric.brier_score)}"
            )
        print(f"Output: {output_dir}")
    return 0


def _cmd_predict_probabilities(args: argparse.Namespace) -> int:
    trade_date = _parse_date(args.date)
    model_path = args.model_dir / "model.json"
    if not args.model_dir.exists() or not model_path.exists():
        raise ValueError(f"model-dir must contain model.json: {args.model_dir}")
    config = load_project_config(args.config_dir)
    model = load_probability_model_json(model_path)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    predictions = ProbabilityPredictor(
        config=config,
        model=model,
        stock_master=adapter.load_stock_master(),
        daily_bars=adapter.load_daily_bars(),
        financial_summary=adapter.load_financial_summary(),
        announcement_events=adapter.load_announcement_events(),
    ).predict_for_date(trade_date)
    output_path = args.output or Path("outputs") / "probability" / f"probability_daily_{trade_date.isoformat()}.csv"
    save_probability_predictions_csv(predictions, output_path)
    summary = {
        "date": trade_date.isoformat(),
        "total_stocks": len(predictions),
        "predictable_count": sum(1 for item in predictions if item.is_predictable),
        "low_confidence_count": sum(1 for item in predictions if item.confidence_level == "low"),
        "output": str(output_path),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Probability predictions generated for {summary['date']}")
        print(f"Total stocks: {summary['total_stocks']}")
        print(f"Predictable stocks: {summary['predictable_count']}")
        print(f"Low confidence: {summary['low_confidence_count']}")
        print(f"Output: {output_path}")
    return 0


def _cmd_audit_leakage(args: argparse.Namespace) -> int:
    has_date = args.date is not None
    has_range = args.start is not None or args.end is not None
    if has_date and has_range:
        raise ValueError("Provide either --date or --start/--end, not both.")
    if not has_date and not (args.start is not None and args.end is not None):
        raise ValueError("Provide --date or both --start and --end.")
    if (args.start is None) != (args.end is None):
        raise ValueError("Provide both --start and --end for range audit.")

    config_dir = args.config_dir or _default_config_dir()
    load_project_config(config_dir)
    adapter = LocalCsvAdapter(args.data_dir)
    validation_report = adapter.validate_all()
    if not validation_report.passed:
        _print_validation_failure(validation_report, args.format)
        return 1

    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summary = adapter.load_financial_summary()
    announcement_events = adapter.load_announcement_events()
    snapshot = build_data_snapshot(
        data_dir=args.data_dir,
        config_dir=config_dir,
        source_name=args.source_name,
        data_version=args.data_version,
        stock_master=stock_master,
        daily_bars=daily_bars,
        financial_summary=financial_summary,
        announcement_events=announcement_events,
    )
    auditor = LeakageAuditor(
        data_dir=args.data_dir,
        config_dir=config_dir,
        source_name=args.source_name,
        data_version=args.data_version,
    )
    if has_date:
        audit_date = _parse_date(args.date)
        report = auditor.audit_records(
            audit_date=audit_date,
            start_date=None,
            end_date=None,
            stock_master=stock_master,
            daily_bars=daily_bars,
            financial_summary=financial_summary,
            announcement_events=announcement_events,
        )
        output_dir = args.output_dir or Path("outputs") / "audit" / f"leakage_{audit_date.isoformat()}"
    else:
        start_date = _parse_date(args.start)
        end_date = _parse_date(args.end)
        if start_date >= end_date:
            raise ValueError("start must be earlier than end.")
        report = auditor.audit_records(
            audit_date=None,
            start_date=start_date,
            end_date=end_date,
            stock_master=stock_master,
            daily_bars=daily_bars,
            financial_summary=financial_summary,
            announcement_events=announcement_events,
        )
        output_dir = args.output_dir or Path("outputs") / "audit" / f"leakage_{start_date.isoformat()}_{end_date.isoformat()}"

    report_json = output_dir / "audit_report.json"
    report_md = output_dir / "audit_report.md"
    snapshot_json = output_dir / "data_snapshot.json"
    save_leakage_audit_report_json(report, report_json)
    save_leakage_audit_report_md(report, report_md)
    save_data_snapshot_json(snapshot, snapshot_json)
    summary = {
        "passed": report.passed,
        "total_issues": report.total_issues,
        "error_count": report.error_count,
        "warning_count": report.warning_count,
        "info_count": report.info_count,
        "output_dir": str(output_dir),
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("Point-in-Time leakage audit completed")
        print(f"Passed: {summary['passed']}")
        print(f"Total issues: {summary['total_issues']}")
        print(f"Errors: {summary['error_count']}")
        print(f"Warnings: {summary['warning_count']}")
        print(f"Info: {summary['info_count']}")
        print(f"Output: {output_dir}")
    return 1 if report.error_count > 0 else 0


def _cmd_run_pipeline(args: argparse.Namespace) -> int:
    pipeline_date = _parse_date(args.date)
    config_dir = args.config_dir or _default_config_dir()
    output_dir = args.output_dir or Path("outputs") / "pipelines" / f"pipeline_{pipeline_date.isoformat()}"
    manifest = PipelineRunner(
        date=pipeline_date,
        data_dir=args.data_dir,
        config_dir=config_dir,
        output_dir=output_dir,
        model_dir=args.model_dir,
        require_probability=args.require_probability,
        audit_leakage=args.audit_leakage,
        quality_report=args.quality_report,
        check_security=args.check_security,
    ).run()
    save_pipeline_manifest(manifest, output_dir / "manifest.json")
    save_pipeline_summary_md(manifest, output_dir / "pipeline_summary.md")
    experiment_id = None
    if args.record_experiment:
        experiment = ExperimentRecorder(ExperimentRegistry(args.experiment_registry_dir)).record_completed_run(
            command="run-pipeline",
            command_args={
                "date": args.date,
                "data_dir": args.data_dir,
                "config_dir": config_dir,
                "model_dir": args.model_dir,
                "require_probability": args.require_probability,
                "audit_leakage": args.audit_leakage,
                "quality_report": args.quality_report,
                "check_security": args.check_security,
                "output_dir": output_dir,
            },
            status=manifest.status,
            output_dir=output_dir,
            data_dir=args.data_dir,
            config_dir=config_dir,
            notes=args.experiment_notes,
            tags=args.experiment_tag,
        )
        experiment_id = experiment.experiment_id
    summary = {
        "date": manifest.pipeline_date.isoformat(),
        "status": manifest.status,
        "total_stocks": manifest.total_stocks,
        "allowed_universe_count": manifest.allowed_universe_count,
        "buy_count": manifest.buy_count,
        "watch_count": manifest.watch_count,
        "block_count": manifest.block_count,
        "high_risk_count": manifest.high_risk_count,
        "market_regime": manifest.market_regime,
        "probability_predictable_count": manifest.probability_predictable_count,
        "output_dir": str(output_dir),
        "experiment_id": experiment_id,
    }
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Pipeline run for {summary['date']}")
        print(f"Status: {summary['status']}")
        if manifest.status == "PARTIAL":
            print("部分步骤失败：请查看 manifest.json 和 pipeline_summary.md。")
        print(f"Total stocks: {summary['total_stocks']}")
        print(f"Allowed universe: {summary['allowed_universe_count']}")
        print(f"BUY: {summary['buy_count']}")
        print(f"WATCH: {summary['watch_count']}")
        print(f"BLOCK: {summary['block_count']}")
        print(f"High risk: {summary['high_risk_count']}")
        print(f"Market regime: {summary['market_regime']}")
        print(f"Probability predictable: {summary['probability_predictable_count']}")
        print(f"Output: {output_dir}")
        if experiment_id:
            print(f"Experiment id: {experiment_id}")
    return 1 if manifest.status == "FAILED" else 0


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc


def _print_validation_failure(report, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return
    print("Data validation failed:")
    for error in report.errors:
        print(f"  - {error}")


def _scan_import_manifests(target_root_dir: Path, source_name: str | None) -> list:
    if not target_root_dir.exists():
        return []
    source_filter = normalize_source_name(source_name) if source_name else None
    manifests = []
    for manifest_path in sorted(target_root_dir.glob("*/*/import_manifest.json")):
        try:
            manifest = load_import_manifest(manifest_path)
        except ValueError:
            continue
        if source_filter is not None and manifest.source_name != source_filter:
            continue
        manifests.append(manifest)
    return manifests


def _import_summary(manifest) -> dict[str, object]:
    return {
        "source_name": manifest.source_name,
        "data_version": manifest.data_version,
        "created_at": manifest.created_at.isoformat(),
        "status": manifest.status,
        "validation_passed": manifest.validation_passed,
        "row_counts": manifest.row_counts,
        "target_data_dir": manifest.target_data_dir,
    }


def _default_config_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "ashare_alpha"


def _walkforward_default_output_root(spec_path: Path) -> Path:
    payload = load_yaml_config(Path(spec_path))
    output_root = payload.get("output_root_dir")
    if not isinstance(output_root, str) or not output_root:
        raise ValueError("walkforward spec output_root_dir must be a non-empty string")
    return Path(output_root)


def _default_mapping_path(source_name: str) -> Path:
    return _default_config_dir() / "data_sources" / f"{source_name}_mapping.yaml"


def _load_source_profile(path: Path) -> SourceProfile:
    return SourceProfile.model_validate(load_yaml_config(Path(path)))


def _source_profile_summary(profile: SourceProfile) -> dict[str, object]:
    return {
        "source_name": profile.source_name,
        "display_name": profile.display_name,
        "mode": profile.mode,
        "enabled": profile.enabled,
        "requires_network": profile.requires_network,
        "requires_api_key": profile.requires_api_key,
        "fixture_dir": profile.fixture_dir,
        "cache_dir": profile.cache_dir,
    }


def _source_runtime_security_summary(security_config) -> dict[str, object]:
    return {
        "offline_mode": security_config.offline_mode,
        "allow_network": security_config.allow_network,
        "allow_broker_connections": security_config.allow_broker_connections,
        "allow_live_trading": security_config.allow_live_trading,
        "allowed_domains": security_config.network_policy.allowed_domains,
    }


def _can_profile_run_offline(profile: SourceProfile, security_config) -> tuple[bool, str | None]:
    context = SourceRuntimeContext(
        profile=profile,
        security_config=security_config,
        network_guard=NetworkGuard(security_config),
        secret_provider=EnvSecretProvider(),
    )
    try:
        context.assert_can_run_offline()
    except RuntimeError as exc:
        return False, str(exc)
    return True, None


def _experiment_record_summary(record, registry_dir: Path) -> dict[str, object]:
    return {
        "experiment_id": record.experiment_id,
        "command": record.command,
        "status": record.status,
        "metrics_count": len(record.metrics),
        "artifacts_count": len(record.artifacts),
        "registry_dir": str(registry_dir),
    }


def _experiment_list_row(record) -> dict[str, object]:
    return {
        "experiment_id": record.experiment_id,
        "created_at": record.created_at.isoformat(),
        "command": record.command,
        "status": record.status,
        "data_source": record.data_source,
        "data_version": record.data_version,
        "config_hash_short": record.config_hash[:8] if record.config_hash else None,
        "metrics_count": len(record.metrics),
        "artifacts_count": len(record.artifacts),
        "tags": record.tags,
    }


def _load_backtest_result(backtest_dir: Path) -> BacktestResult:
    metrics_path = backtest_dir / "metrics.json"
    trades_path = backtest_dir / "trades.csv"
    daily_equity_path = backtest_dir / "daily_equity.csv"
    missing = [path.name for path in (metrics_path, trades_path, daily_equity_path) if not path.exists()]
    if missing:
        raise ValueError(f"reuse backtest dir missing required files: {', '.join(missing)}")

    metrics_payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics_payload["start_date"] = _parse_date(metrics_payload["start_date"])
    metrics_payload["end_date"] = _parse_date(metrics_payload["end_date"])
    metrics = BacktestMetrics(**metrics_payload)
    trades = [_trade_from_row(row) for row in _read_csv_rows(trades_path)]
    daily_equity = [_daily_equity_from_row(row) for row in _read_csv_rows(daily_equity_path)]
    return BacktestResult(metrics=metrics, trades=trades, daily_equity=daily_equity)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _trade_from_row(row: dict[str, str]) -> SimulatedTrade:
    payload = {field.name: row.get(field.name) for field in fields(SimulatedTrade)}
    for key in ("decision_date", "execution_date"):
        payload[key] = _parse_date(str(payload[key]))
    for key in ("requested_shares", "filled_shares"):
        payload[key] = int(float(payload[key] or 0))
    for key in (
        "price",
        "gross_value",
        "commission",
        "stamp_tax",
        "transfer_fee",
        "total_fee",
        "net_cash_change",
        "realized_pnl",
    ):
        payload[key] = _optional_float(payload[key])
    payload["holding_days"] = _optional_int(payload["holding_days"])
    payload["reject_reason"] = payload["reject_reason"] or None
    return SimulatedTrade(**payload)


def _daily_equity_from_row(row: dict[str, str]) -> DailyEquityRecord:
    payload = {field.name: row.get(field.name) for field in fields(DailyEquityRecord)}
    payload["trade_date"] = _parse_date(str(payload["trade_date"]))
    payload["positions_count"] = int(float(payload["positions_count"] or 0))
    for key in ("cash", "market_value", "total_equity", "gross_exposure", "daily_return", "drawdown"):
        payload[key] = float(payload[key] or 0)
    return DailyEquityRecord(**payload)


def _optional_float(value: object) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _optional_int(value: object) -> int | None:
    if value in {None, ""}:
        return None
    return int(float(value))


def _format_optional(value: float | None) -> str:
    return "None" if value is None else f"{value:.4f}"


def _data_source_summary(source: DataSourceMetadata, security_config=None) -> dict[str, object]:
    capabilities = source.capabilities
    summary = {
        "name": source.name,
        "display_name": source.display_name,
        "status": source.status,
        "supports_stock_master": capabilities.supports_stock_master,
        "supports_daily_bar": capabilities.supports_daily_bar,
        "requires_network": capabilities.requires_network,
        "requires_api_key": capabilities.requires_api_key,
        "is_live_trading_source": capabilities.is_live_trading_source,
    }
    if security_config is not None:
        summary.update(_data_source_security_summary(source.name, security_config))
    return summary


def _data_source_security_summary(source_name: str, security_config) -> dict[str, object]:
    source_security = security_config.data_sources.get(source_name)
    if source_security is None:
        return {
            "security_enabled": False,
            "security_requires_network": None,
            "security_requires_api_key": None,
            "security_api_key_env_var": None,
            "secret_is_set": False,
        }
    env_var = source_security.api_key_env_var
    return {
        "security_enabled": source_security.enabled,
        "security_requires_network": source_security.requires_network,
        "security_requires_api_key": source_security.requires_api_key,
        "security_api_key_env_var": env_var,
        "secret_is_set": bool(safe_env_status(env_var)["is_set"]) if env_var else False,
    }
