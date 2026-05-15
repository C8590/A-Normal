from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from ashare_alpha.data.contracts import (
    ExternalContractValidationIssue,
    ExternalContractValidationReport,
    ExternalDatasetContract,
)


def test_external_dataset_contract_accepts_valid_payload() -> None:
    contract = ExternalDatasetContract(
        source_name="tushare_like",
        dataset_name="daily",
        required_fields=["ts_code", "trade_date"],
        optional_fields=["pct_chg"],
        target_dataset_name="daily_bar",
        description="daily fixture",
    )

    assert contract.source_name == "tushare_like"
    assert contract.target_dataset_name == "daily_bar"


def test_external_contract_validation_report_accepts_valid_payload() -> None:
    issue = ExternalContractValidationIssue(
        severity="info",
        source_name="tushare_like",
        dataset_name="daily",
        issue_type="missing_optional_field",
        field_name="pct_chg",
        message="Optional field is missing.",
        recommendation="Add it when needed.",
    )

    report = ExternalContractValidationReport(
        source_name="tushare_like",
        fixture_dir="tests/fixtures/external_sources/tushare_like",
        generated_at=datetime.now(),
        total_issues=1,
        error_count=0,
        warning_count=0,
        info_count=1,
        passed=True,
        issues=[issue],
        row_counts={"daily": 1},
        summary="ok",
    )

    assert report.passed is True


def test_external_contract_validation_issue_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        ExternalContractValidationIssue(
            severity="critical",
            source_name="tushare_like",
            dataset_name="daily",
            issue_type="bad",
            field_name=None,
            message="bad",
            recommendation="fix",
        )
