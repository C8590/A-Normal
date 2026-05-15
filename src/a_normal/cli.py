from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

from a_normal.backtest import run_backtest, save_backtest_reports
from a_normal.config import load_config
from a_normal.data import LocalCsvAdapter
from a_normal.factors import build_factor_daily, save_factor_daily_csv, score_announcement_events
from a_normal.models import train_probability_model
from a_normal.reports import generate_daily_report, save_daily_report
from a_normal.signals import build_signals, load_scoring_config, save_signals_csv, save_signals_markdown
from a_normal.universe import build_universe_daily, load_universe_config


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ashare-alpha",
        description="A-share alpha research CLI using local CSV sample data by default.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate-data", help="Validate local CSV data and configs.")
    _add_common_io(validate_parser, output_default="outputs/validation")
    validate_parser.set_defaults(handler=_cmd_validate_data)

    universe_parser = subparsers.add_parser("build-universe", help="Build daily tradable universe.")
    universe_parser.add_argument("--date", required=True, help="Trading date, format YYYY-MM-DD.")
    _add_common_io(universe_parser, output_default="outputs/universe")
    universe_parser.set_defaults(handler=_cmd_build_universe)

    factor_parser = subparsers.add_parser("compute-factors", help="Compute factor_daily for one date.")
    factor_parser.add_argument("--date", required=True, help="Trading date, format YYYY-MM-DD.")
    _add_common_io(factor_parser, output_default="outputs/factors")
    factor_parser.set_defaults(handler=_cmd_compute_factors)

    signal_parser = subparsers.add_parser("generate-signals", help="Generate stock signals for one date.")
    signal_parser.add_argument("--date", required=True, help="Trading date, format YYYY-MM-DD.")
    signal_parser.add_argument("--market-regime", default="normal", choices=["normal", "risk"], help="Market regime.")
    _add_common_io(signal_parser, output_default="outputs/signals")
    signal_parser.set_defaults(handler=_cmd_generate_signals)

    backtest_parser = subparsers.add_parser("run-backtest", help="Run backtest between start and end dates.")
    backtest_parser.add_argument("--start", default=None, help="Start date, format YYYY-MM-DD.")
    backtest_parser.add_argument("--end", default=None, help="End date, format YYYY-MM-DD.")
    backtest_parser.add_argument("--date", default=None, help="Backward-compatible end date alias.")
    backtest_parser.add_argument("--market-regime", default="normal", choices=["normal", "risk"], help="Market regime.")
    _add_common_io(backtest_parser, output_default="outputs/backtests")
    backtest_parser.set_defaults(handler=_cmd_run_backtest)

    report_parser = subparsers.add_parser("report", help="Generate daily Markdown, CSV, and JSON report.")
    report_parser.add_argument("--date", required=True, help="Trading date, format YYYY-MM-DD.")
    report_parser.add_argument("--market-regime", default="normal", choices=["normal", "risk"], help="Market regime.")
    _add_common_io(report_parser, output_default="outputs/reports")
    report_parser.set_defaults(handler=_cmd_report)

    pipeline_parser = subparsers.add_parser("run-pipeline", help="Run validation, universe, factors, signals, report, and backtest.")
    pipeline_parser.add_argument("--date", required=True, help="Pipeline date, format YYYY-MM-DD.")
    pipeline_parser.add_argument("--market-regime", default="normal", choices=["normal", "risk"], help="Market regime.")
    _add_common_io(pipeline_parser, output_default="outputs")
    pipeline_parser.set_defaults(handler=_cmd_run_pipeline)

    probability_parser = subparsers.add_parser("train-probability", help="Train baseline probability model.")
    probability_parser.add_argument("--min-samples", type=int, default=30, help="Minimum labeled samples required.")
    _add_common_io(probability_parser, output_default="outputs/models")
    probability_parser.set_defaults(handler=_cmd_train_probability)
    return parser


def _add_common_io(parser: argparse.ArgumentParser, output_default: str) -> None:
    parser.add_argument("--data-dir", default=None, help="Directory containing local CSV files. Defaults to data/sample.")
    parser.add_argument("--config-dir", default=None, help="Directory containing YAML configs. Defaults to configs/.")
    parser.add_argument("--output-dir", default=output_default, help=f"Output directory. Default: {output_default}.")


def _cmd_validate_data(args: argparse.Namespace) -> int:
    adapter = _adapter(args)
    app_config = load_config(args.config_dir)
    stock_master = adapter.load_stock_master()
    daily_bars = adapter.load_daily_bars()
    financial_summaries = adapter.load_financial_summaries()
    announcement_events = adapter.load_announcement_events()
    summary = {
        "status": "ok",
        "stock_master_rows": len(stock_master),
        "daily_bar_rows": len(daily_bars),
        "financial_summary_rows": len(financial_summaries),
        "announcement_event_rows": len(announcement_events),
        "trading_rules": app_config.trading_rules.model_dump(mode="json"),
        "fees": app_config.fees.model_dump(mode="json"),
    }
    path = _output_dir(args) / "validation_summary.json"
    _write_json(path, summary)
    print("Data validation passed.")
    print(f"Summary: {path}")
    return 0


def _cmd_build_universe(args: argparse.Namespace) -> int:
    _parse_date(args.date)
    result = build_universe_daily(args.date, adapter=_adapter(args), config=load_universe_config(args.config_dir))
    path = _output_dir(args) / f"universe_daily_{args.date}.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        _write_universe_rows(writer, result.rows)

    writer = csv.writer(sys.stdout, lineterminator="\n")
    _write_universe_rows(writer, result.rows)
    print(f"Output: {path}")
    return 0


def _cmd_compute_factors(args: argparse.Namespace) -> int:
    _parse_date(args.date)
    factors = build_factor_daily(_adapter(args).load_daily_bars(), as_of_date=args.date)
    path = _output_dir(args) / f"factor_daily_{args.date}.csv"
    save_factor_daily_csv(factors, path)
    print(f"Rows: {len(factors)}")
    print(f"CSV: {path}")
    return 0


def _cmd_generate_signals(args: argparse.Namespace) -> int:
    signals = _signals_for_date(args.date, args.market_regime, _adapter(args), args.config_dir)
    output_dir = _output_dir(args)
    csv_path = output_dir / f"signals_{args.date}.csv"
    markdown_path = output_dir / f"signals_{args.date}.md"
    save_signals_csv(signals, csv_path)
    save_signals_markdown(signals, markdown_path, title=f"A股信号报告 {args.date}")
    print(f"CSV: {csv_path}")
    print(f"Markdown: {markdown_path}")
    return 0


def _cmd_run_backtest(args: argparse.Namespace) -> int:
    adapter = _adapter(args)
    daily_bars = adapter.load_daily_bars()
    start_date, end_date = _backtest_dates(args, daily_bars)
    date_values = sorted({bar.trade_date for bar in daily_bars if start_date <= bar.trade_date <= end_date})
    if not date_values:
        raise ValueError(f"No trading dates found between {start_date} and {end_date}.")

    all_signals = []
    for trade_date in date_values:
        all_signals.extend(_signals_for_date(trade_date.isoformat(), args.market_regime, adapter, args.config_dir))
    scoring_config = load_scoring_config(args.config_dir)
    result = run_backtest(daily_bars, all_signals, initial_cash=scoring_config.capital)
    output_dir = _output_dir(args)
    paths = save_backtest_reports(result, output_dir)
    print(f"Report: {paths['report']}")
    print(f"Daily NAV: {paths['daily_nav']}")
    print(f"Trades: {paths['trades']}")
    print(f"Metrics: {paths['metrics']}")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    report = generate_daily_report(args.date, market_regime=args.market_regime, adapter=_adapter(args), config_dir=args.config_dir)
    paths = save_daily_report(report, _output_dir(args))
    print(f"Markdown: {paths['markdown']}")
    print(f"CSV: {paths['csv']}")
    print(f"JSON: {paths['json']}")
    return 0


def _cmd_run_pipeline(args: argparse.Namespace) -> int:
    base = _output_dir(args)
    validate_args = _replace_namespace(args, output_dir=str(base / "validation"))
    universe_args = _replace_namespace(args, output_dir=str(base / "universe"))
    factor_args = _replace_namespace(args, output_dir=str(base / "factors"))
    signal_args = _replace_namespace(args, output_dir=str(base / "signals"))
    report_args = _replace_namespace(args, output_dir=str(base / "reports"))
    backtest_args = _replace_namespace(args, start=None, end=args.date, output_dir=str(base / "backtests"))

    _cmd_validate_data(validate_args)
    _cmd_build_universe(universe_args)
    _cmd_compute_factors(factor_args)
    _cmd_generate_signals(signal_args)
    _cmd_report(report_args)
    _cmd_run_backtest(backtest_args)
    print(f"Pipeline completed: {base}")
    return 0


def _cmd_train_probability(args: argparse.Namespace) -> int:
    result = train_probability_model(_adapter(args).load_daily_bars(), min_samples=args.min_samples)
    path = _output_dir(args) / "baseline_probability_model.json"
    _write_json(path, result.model_dump(mode="json"))
    print(f"Status: {result.status}")
    print(f"Output: {path}")
    return 0


def _signals_for_date(date_text: str, market_regime: str, adapter: LocalCsvAdapter, config_dir: str | None) -> list:
    _parse_date(date_text)
    universe_config = load_universe_config(config_dir)
    scoring_config = load_scoring_config(config_dir)
    universe_result = build_universe_daily(date_text, adapter=adapter, config=universe_config)
    factor_rows = build_factor_daily(adapter.load_daily_bars(), as_of_date=date_text)
    event_rows = score_announcement_events(adapter.load_announcement_events(), as_of_date=date_text)
    return build_signals(
        list(universe_result.rows),
        factor_rows,
        event_rows,
        market_regime=market_regime,
        as_of_date=date_text,
        config=scoring_config,
    )


def _write_universe_rows(writer, rows) -> None:
    writer.writerow(["ts_code", "is_allowed", "exclude_reasons", "liquidity_score", "risk_score"])
    for row in rows:
        writer.writerow([row.ts_code, str(row.is_allowed).lower(), ";".join(row.exclude_reasons), row.liquidity_score, row.risk_score])


def _backtest_dates(args: argparse.Namespace, daily_bars) -> tuple[date, date]:
    end_text = args.end or args.date
    if end_text is None:
        raise ValueError("run-backtest requires --end YYYY-MM-DD, or --date YYYY-MM-DD for backward compatibility.")
    end_date = _parse_date(end_text)
    start_date = _parse_date(args.start) if args.start else min(bar.trade_date for bar in daily_bars)
    if start_date > end_date:
        raise ValueError("--start must be earlier than or equal to --end.")
    return start_date, end_date


def _adapter(args: argparse.Namespace) -> LocalCsvAdapter:
    return LocalCsvAdapter(Path(args.data_dir) if args.data_dir else None)


def _output_dir(args: argparse.Namespace) -> Path:
    path = Path(args.output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_date(value: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _replace_namespace(args: argparse.Namespace, **updates) -> argparse.Namespace:
    values = vars(args).copy()
    values.update(updates)
    return argparse.Namespace(**values)


if __name__ == "__main__":
    raise SystemExit(main())
