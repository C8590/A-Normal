from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ashare_alpha.adjusted.models import AdjustedDailyBarRecord, AdjustedQualityFlag


AdjustedIssueSeverity = Literal["info", "warning", "error"]


class AdjustedValidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdjustedValidationIssue(AdjustedValidationModel):
    severity: AdjustedIssueSeverity
    ts_code: str | None = None
    trade_date: date | None = None
    issue_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    recommendation: str = Field(min_length=1)


class AdjustedValidationReport(AdjustedValidationModel):
    total_records: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    info_count: int = Field(ge=0)
    passed: bool
    issues: list[AdjustedValidationIssue] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> AdjustedValidationReport:
        if self.issue_count != len(self.issues):
            raise ValueError("issue_count must equal len(issues)")
        if self.error_count != sum(1 for issue in self.issues if issue.severity == "error"):
            raise ValueError("error_count does not match issues")
        if self.warning_count != sum(1 for issue in self.issues if issue.severity == "warning"):
            raise ValueError("warning_count does not match issues")
        if self.info_count != sum(1 for issue in self.issues if issue.severity == "info"):
            raise ValueError("info_count does not match issues")
        if self.passed != (self.error_count == 0):
            raise ValueError("passed must be true only when error_count is 0")
        return self


def validate_adjusted_records(records: list[AdjustedDailyBarRecord]) -> AdjustedValidationReport:
    issues: list[AdjustedValidationIssue] = []
    for record in records:
        if record.adj_type != "raw" and record.adj_close is None:
            issues.append(_issue("error", record, "missing_adj_close", "adj_close is missing.", "Check adjustment factors and raw close."))
        if record.adj_type != "raw" and record.adj_factor is None:
            issues.append(_issue("error", record, "missing_adj_factor", "adj_factor is missing.", "Populate same-day adjustment_factor rows."))
        if record.adj_high is not None and record.adj_low is not None and record.adj_high < record.adj_low:
            issues.append(_issue("error", record, "adj_high_below_low", "adj_high is lower than adj_low.", "Check adjusted price formula and raw OHLC."))
        if record.adj_low is not None:
            if record.adj_open is not None and record.adj_low > record.adj_open:
                issues.append(_issue("error", record, "adj_low_above_open", "adj_low is above adj_open.", "Check adjusted OHLC consistency."))
            if record.adj_close is not None and record.adj_low > record.adj_close:
                issues.append(_issue("error", record, "adj_low_above_close", "adj_low is above adj_close.", "Check adjusted OHLC consistency."))
        if record.adj_high is not None:
            if record.adj_open is not None and record.adj_high < record.adj_open:
                issues.append(_issue("error", record, "adj_high_below_open", "adj_high is below adj_open.", "Check adjusted OHLC consistency."))
            if record.adj_close is not None and record.adj_high < record.adj_close:
                issues.append(_issue("error", record, "adj_high_below_close", "adj_high is below adj_close.", "Check adjusted OHLC consistency."))
        if record.adj_return_1d is not None and abs(record.adj_return_1d) > 0.5:
            issues.append(_issue("warning", record, "extreme_adj_return_1d", "adj_return_1d absolute value is above 50%.", "Review factor changes, raw prices, and corporate actions."))
        for flag in record.quality_flags:
            severity = _severity_for_flag(flag)
            issues.append(_issue(severity, record, flag.lower(), _message_for_flag(flag), _recommendation_for_flag(flag)))

    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    info_count = sum(1 for issue in issues if issue.severity == "info")
    return AdjustedValidationReport(
        total_records=len(records),
        issue_count=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        passed=error_count == 0,
        issues=issues,
    )


def _issue(
    severity: AdjustedIssueSeverity,
    record: AdjustedDailyBarRecord,
    issue_type: str,
    message: str,
    recommendation: str,
) -> AdjustedValidationIssue:
    return AdjustedValidationIssue(
        severity=severity,
        ts_code=record.ts_code,
        trade_date=record.trade_date,
        issue_type=issue_type,
        message=message,
        recommendation=recommendation,
    )


def _severity_for_flag(flag: str) -> AdjustedIssueSeverity:
    error_flags = {
        AdjustedQualityFlag.MISSING_ADJ_FACTOR.value,
        AdjustedQualityFlag.INVALID_ADJ_FACTOR.value,
        AdjustedQualityFlag.MISSING_BASE_FACTOR.value,
        AdjustedQualityFlag.INVALID_RAW_PRICE.value,
        AdjustedQualityFlag.INVALID_ADJUSTED_PRICE.value,
    }
    info_flags = {AdjustedQualityFlag.FALLBACK_ADJ_TYPE.value}
    if flag in error_flags:
        return "error"
    if flag in info_flags:
        return "info"
    return "warning"


def _message_for_flag(flag: str) -> str:
    messages = {
        AdjustedQualityFlag.MISSING_ADJ_FACTOR.value: "Same-day adjustment factor is missing.",
        AdjustedQualityFlag.INVALID_ADJ_FACTOR.value: "Adjustment factor is invalid.",
        AdjustedQualityFlag.FALLBACK_ADJ_TYPE.value: "Requested adj_type was missing and qfq factor was used as fallback.",
        AdjustedQualityFlag.MISSING_BASE_FACTOR.value: "Base adjustment factor is missing.",
        AdjustedQualityFlag.INVALID_RAW_PRICE.value: "Raw OHLC price relationship is invalid.",
        AdjustedQualityFlag.INVALID_ADJUSTED_PRICE.value: "Adjusted OHLC price relationship is invalid.",
        AdjustedQualityFlag.CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE.value: "Corporate action has no nearby factor change.",
        AdjustedQualityFlag.FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION.value: "Factor changes without a nearby corporate action.",
        AdjustedQualityFlag.STALE_FACTOR.value: "Historical factor exists but the same-day factor is missing.",
        AdjustedQualityFlag.MISSING_FACTOR_AVAILABLE_AT.value: "Adjustment factor available_at is missing.",
    }
    return messages.get(flag, flag)


def _recommendation_for_flag(flag: str) -> str:
    recommendations = {
        AdjustedQualityFlag.MISSING_ADJ_FACTOR.value: "Populate adjustment_factor for the stock, date, and adj_type.",
        AdjustedQualityFlag.INVALID_ADJ_FACTOR.value: "Fix nonpositive or malformed adjustment_factor values.",
        AdjustedQualityFlag.FALLBACK_ADJ_TYPE.value: "Provide the requested adj_type if exact qfq/hfq semantics are required.",
        AdjustedQualityFlag.MISSING_BASE_FACTOR.value: "Provide at least one valid factor inside the build range.",
        AdjustedQualityFlag.INVALID_RAW_PRICE.value: "Fix daily_bar raw OHLC fields.",
        AdjustedQualityFlag.INVALID_ADJUSTED_PRICE.value: "Review adjustment ratio and adjusted OHLC values.",
        AdjustedQualityFlag.CORPORATE_ACTION_WITHOUT_FACTOR_CHANGE.value: "Check whether the corporate action should affect factors.",
        AdjustedQualityFlag.FACTOR_CHANGE_WITHOUT_CORPORATE_ACTION.value: "Check whether a corporate action row is missing.",
        AdjustedQualityFlag.STALE_FACTOR.value: "Backfill same-day adjustment factors before using adjusted prices.",
        AdjustedQualityFlag.MISSING_FACTOR_AVAILABLE_AT.value: "Populate source-visible available_at for point-in-time auditability.",
    }
    return recommendations.get(flag, "Review adjusted bar quality flag.")
