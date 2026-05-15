from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ashare_alpha.data.contracts import (
    ExternalContractValidationReport,
    ExternalConversionResult,
    save_contract_report_json,
    save_contract_report_md,
    save_conversion_result_json,
)


def test_contract_report_json_can_be_saved(tmp_path: Path) -> None:
    output_path = tmp_path / "contract_report.json"

    save_contract_report_json(_report(), output_path)

    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True


def test_contract_report_md_can_be_saved(tmp_path: Path) -> None:
    output_path = tmp_path / "contract_report.md"

    save_contract_report_md(_report(), output_path)

    assert "外部数据源契约检查报告" in output_path.read_text(encoding="utf-8")


def test_conversion_result_json_can_be_saved(tmp_path: Path) -> None:
    output_path = tmp_path / "conversion_result.json"
    result = ExternalConversionResult(
        source_name="tushare_like",
        fixture_dir="fixture",
        output_dir="output",
        generated_files=["output/stock_master.csv"],
        row_counts={"stock_master": 1},
        validation_passed=True,
        validation_errors=[],
        summary="ok",
    )

    save_conversion_result_json(result, output_path)

    assert json.loads(output_path.read_text(encoding="utf-8"))["validation_passed"] is True


def _report() -> ExternalContractValidationReport:
    return ExternalContractValidationReport(
        source_name="tushare_like",
        fixture_dir="fixture",
        generated_at=datetime.now(),
        total_issues=0,
        error_count=0,
        warning_count=0,
        info_count=0,
        passed=True,
        issues=[],
        row_counts={"daily": 1},
        summary="ok",
    )
