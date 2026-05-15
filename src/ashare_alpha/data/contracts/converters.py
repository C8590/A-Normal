from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ashare_alpha.data.adapters.local_csv import LocalCsvAdapter
from ashare_alpha.data.contracts.validator import ExternalContractValidator


class ExternalConversionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_name: str = Field(min_length=1)
    fixture_dir: str
    output_dir: str
    generated_files: list[str] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    validation_passed: bool
    validation_errors: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)


class ExternalFixtureConverter:
    def __init__(self, source_name: str, fixture_dir: Path, mapping_path: Path, output_dir: Path) -> None:
        self.source_name = source_name.strip().lower()
        self.fixture_dir = Path(fixture_dir)
        self.mapping_path = Path(mapping_path)
        self.output_dir = Path(output_dir)

    def convert(self) -> ExternalConversionResult:
        contract_report = ExternalContractValidator(self.source_name, self.fixture_dir).validate()
        if not contract_report.passed:
            errors = [issue.message for issue in contract_report.issues if issue.severity == "error"]
            raise ValueError("External fixture contract validation failed: " + "; ".join(errors))

        mapping_config = self._load_mapping_config()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        generated_files: list[str] = []

        for dataset_name, dataset_mapping in mapping_config["datasets"].items():
            target_dataset = dataset_mapping["target_dataset"]
            rows = self._convert_dataset(dataset_name, dataset_mapping)
            output_path = self.output_dir / f"{target_dataset}.csv"
            self._write_rows(output_path, target_dataset, rows)
            generated_files.append(str(output_path))

        validation_report = LocalCsvAdapter(self.output_dir).validate_all()
        summary = (
            f"External fixture conversion completed for {self.source_name}: "
            f"validation_passed={validation_report.passed}."
        )
        return ExternalConversionResult(
            source_name=self.source_name,
            fixture_dir=str(self.fixture_dir),
            output_dir=str(self.output_dir),
            generated_files=generated_files,
            row_counts=validation_report.row_counts,
            validation_passed=validation_report.passed,
            validation_errors=validation_report.errors,
            summary=summary,
        )

    def _load_mapping_config(self) -> dict[str, Any]:
        if not self.mapping_path.exists():
            raise ValueError(f"Mapping YAML does not exist: {self.mapping_path}")
        payload = yaml.safe_load(self.mapping_path.read_text(encoding="utf-8")) or {}
        if payload.get("source_name") != self.source_name:
            raise ValueError(f"Mapping YAML source_name must be {self.source_name}: {self.mapping_path}")
        if not isinstance(payload.get("datasets"), dict):
            raise ValueError(f"Mapping YAML must contain a datasets mapping: {self.mapping_path}")
        return payload

    def _convert_dataset(self, dataset_name: str, dataset_mapping: dict[str, Any]) -> list[dict[str, Any]]:
        input_path = self.fixture_dir / f"{dataset_name}.csv"
        field_mapping = dataset_mapping.get("field_mapping") or {}
        defaults = dataset_mapping.get("defaults") or {}
        if not isinstance(field_mapping, dict) or not isinstance(defaults, dict):
            raise ValueError(f"Invalid mapping shape for dataset: {dataset_name}")

        with input_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            rows: list[dict[str, Any]] = []
            for raw_row in reader:
                converted: dict[str, Any] = {}
                for source_field, target_field in field_mapping.items():
                    if source_field in raw_row:
                        converted[target_field] = raw_row.get(source_field, "")
                for target_field, default_value in defaults.items():
                    if _is_blank(converted.get(target_field)):
                        converted[target_field] = default_value
                self._standardize_row(dataset_mapping["target_dataset"], converted)
                rows.append(converted)
            return rows

    def _standardize_row(self, target_dataset: str, row: dict[str, Any]) -> None:
        if "exchange" in row:
            row["exchange"] = _normalize_exchange(row.get("exchange"))
        if "board" in row:
            row["board"] = _normalize_board(row.get("board"), row.get("ts_code"))

        if "ts_code" in row:
            row["ts_code"] = _normalize_ts_code(row.get("ts_code"), row.get("exchange"))
        if target_dataset == "stock_master":
            if _is_blank(row.get("symbol")) and not _is_blank(row.get("ts_code")):
                row["symbol"] = str(row["ts_code"]).split(".")[0]
            if _is_blank(row.get("exchange")):
                row["exchange"] = _infer_exchange(row.get("ts_code"))
            if _is_blank(row.get("board")):
                row["board"] = _infer_board(row.get("ts_code"))

        for field_name in ("list_date", "delist_date", "trade_date", "report_date", "publish_date"):
            if field_name in row:
                row[field_name] = _normalize_date(row.get(field_name))
        if "event_time" in row:
            row["event_time"] = _normalize_datetime(row.get("event_time"))

        if target_dataset == "announcement_event":
            if _is_blank(row.get("source")):
                row["source"] = self.source_name
            if _is_blank(row.get("event_type")):
                row["event_type"] = "unknown"

    def _write_rows(self, output_path: Path, target_dataset: str, rows: list[dict[str, Any]]) -> None:
        fieldnames = _target_fieldnames(target_dataset)
        with output_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field_name: _csv_value(row.get(field_name)) for field_name in fieldnames})


def _target_fieldnames(target_dataset: str) -> list[str]:
    fieldnames = {
        "stock_master": [
            "ts_code",
            "symbol",
            "name",
            "exchange",
            "board",
            "industry",
            "list_date",
            "delist_date",
            "is_st",
            "is_star_st",
            "is_suspended",
            "is_delisting_risk",
        ],
        "daily_bar": [
            "trade_date",
            "ts_code",
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            "volume",
            "amount",
            "turnover_rate",
            "limit_up",
            "limit_down",
            "is_trading",
        ],
        "financial_summary": [
            "report_date",
            "publish_date",
            "ts_code",
            "revenue_yoy",
            "profit_yoy",
            "net_profit_yoy",
            "roe",
            "gross_margin",
            "debt_to_asset",
            "operating_cashflow_to_profit",
            "goodwill_to_equity",
        ],
        "announcement_event": [
            "event_time",
            "ts_code",
            "title",
            "source",
            "event_type",
            "event_direction",
            "event_strength",
            "event_risk_level",
            "raw_text",
        ],
    }
    if target_dataset not in fieldnames:
        raise ValueError(f"Unsupported target dataset: {target_dataset}")
    return fieldnames[target_dataset]


def _normalize_exchange(value: Any) -> str:
    text = _clean(value).lower()
    if text in {"sse", "sh", "上海", "上交所", "shse"}:
        return "sse"
    if text in {"szse", "sz", "深圳", "深交所"}:
        return "szse"
    if text in {"bse", "bj", "北交所", "北京"}:
        return "bse"
    return text


def _normalize_board(value: Any, ts_code: Any = None) -> str:
    text = _clean(value).lower()
    if text in {"主板", "main", "主板a股", "main_board", "a股主板"}:
        return "main"
    if text in {"创业板", "chinext", "gem"}:
        return "chinext"
    if text in {"科创板", "star", "star_market"}:
        return "star"
    if text in {"北交所", "bse", "bj"}:
        return "bse"
    inferred = _infer_board(ts_code)
    return inferred if inferred else text


def _normalize_ts_code(value: Any, exchange: Any = None) -> str:
    text = _clean(value).upper()
    if not text:
        return text
    if "." in text:
        symbol, suffix = text.split(".", 1)
        suffix = {"SH": "SH", "SSE": "SH", "SZ": "SZ", "SZSE": "SZ", "BJ": "BJ", "BSE": "BJ"}.get(suffix, suffix)
        return f"{symbol}.{suffix}"
    suffix = _suffix_from_exchange(exchange) or _infer_suffix_from_symbol(text)
    return f"{text}.{suffix}" if suffix else text


def _suffix_from_exchange(exchange: Any) -> str | None:
    normalized = _normalize_exchange(exchange)
    if normalized == "sse":
        return "SH"
    if normalized == "szse":
        return "SZ"
    if normalized == "bse":
        return "BJ"
    return None


def _infer_suffix_from_symbol(symbol: str) -> str | None:
    if symbol.startswith(("600", "601", "603", "605", "688")):
        return "SH"
    if symbol.startswith(("000", "001", "002", "003", "300")):
        return "SZ"
    if symbol.startswith(("8", "9")):
        return "BJ"
    return None


def _infer_exchange(ts_code: Any) -> str:
    suffix = _normalize_ts_code(ts_code).split(".")[-1].upper()
    if suffix == "SH":
        return "sse"
    if suffix == "SZ":
        return "szse"
    if suffix == "BJ":
        return "bse"
    return ""


def _infer_board(ts_code: Any) -> str:
    symbol = _normalize_ts_code(ts_code).split(".")[0]
    if symbol.startswith("300"):
        return "chinext"
    if symbol.startswith("688"):
        return "star"
    if symbol.startswith(("8", "9")):
        return "bse"
    if symbol.startswith(("000", "001", "002", "003", "600", "601", "603", "605")):
        return "main"
    return ""


def _normalize_date(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    if len(text) == 8 and text.isdigit():
        return date(int(text[:4]), int(text[4:6]), int(text[6:8])).isoformat()
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return text


def _normalize_datetime(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    if len(text) == 8 and text.isdigit():
        return datetime(int(text[:4]), int(text[4:6]), int(text[6:8])).isoformat()
    try:
        return datetime.fromisoformat(text.replace(" ", "T")).isoformat()
    except ValueError:
        return text


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _is_blank(value: Any) -> bool:
    return _clean(value) == ""
