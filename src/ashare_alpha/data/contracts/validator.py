from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from ashare_alpha.data.contracts.models import (
    ExternalContractValidationIssue,
    ExternalContractValidationReport,
    ExternalDatasetContract,
)
from ashare_alpha.data.contracts.schemas import get_external_contracts


class ExternalContractValidator:
    def __init__(self, source_name: str, fixture_dir: Path) -> None:
        self.source_name = source_name.strip().lower()
        self.fixture_dir = Path(fixture_dir)

    def validate(self) -> ExternalContractValidationReport:
        issues: list[ExternalContractValidationIssue] = []
        row_counts: dict[str, int] = {}

        try:
            contracts = get_external_contracts(self.source_name)
        except ValueError as exc:
            issues.append(
                self._issue(
                    dataset_name="__source__",
                    severity="error",
                    issue_type="unsupported_source",
                    field_name=None,
                    message=str(exc),
                    recommendation="Use a source_name with an offline contract, such as tushare_like or akshare_like.",
                )
            )
            return self._report(issues, row_counts)

        if not self.fixture_dir.exists():
            for contract in contracts:
                row_counts[contract.dataset_name] = 0
            issues.append(
                self._issue(
                    dataset_name="__fixture_dir__",
                    severity="error",
                    issue_type="missing_fixture_dir",
                    field_name=None,
                    message=f"Fixture directory does not exist: {self.fixture_dir}",
                    recommendation="Create the fixture directory and add the required external CSV files.",
                )
            )
            return self._report(issues, row_counts)

        if not self.fixture_dir.is_dir():
            issues.append(
                self._issue(
                    dataset_name="__fixture_dir__",
                    severity="error",
                    issue_type="fixture_dir_not_directory",
                    field_name=None,
                    message=f"Fixture path is not a directory: {self.fixture_dir}",
                    recommendation="Pass a directory that contains the source fixture CSV files.",
                )
            )
            return self._report(issues, row_counts)

        for contract in contracts:
            self._validate_dataset(contract, issues, row_counts)

        return self._report(issues, row_counts)

    def _validate_dataset(
        self,
        contract: ExternalDatasetContract,
        issues: list[ExternalContractValidationIssue],
        row_counts: dict[str, int],
    ) -> None:
        path = self.fixture_dir / f"{contract.dataset_name}.csv"
        row_counts[contract.dataset_name] = 0
        if not path.exists():
            issues.append(
                self._issue(
                    dataset_name=contract.dataset_name,
                    severity="error",
                    issue_type="missing_csv",
                    field_name=None,
                    message=f"Missing required fixture CSV: {path}",
                    recommendation="Add the CSV file required by the external dataset contract.",
                )
            )
            return
        if not path.is_file():
            issues.append(
                self._issue(
                    dataset_name=contract.dataset_name,
                    severity="error",
                    issue_type="csv_path_not_file",
                    field_name=None,
                    message=f"Fixture CSV path is not a file: {path}",
                    recommendation="Replace the path with a regular CSV file.",
                )
            )
            return

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                fieldnames = {field.strip() for field in reader.fieldnames or [] if field is not None}
                missing_required = sorted(set(contract.required_fields) - fieldnames)
                for field_name in missing_required:
                    issues.append(
                        self._issue(
                            dataset_name=contract.dataset_name,
                            severity="error",
                            issue_type="missing_required_field",
                            field_name=field_name,
                            message=f"Required field is missing: {field_name}",
                            recommendation="Add the field to the fixture or update the contract only if the adapter design changes.",
                        )
                    )
                for field_name in sorted(set(contract.optional_fields) - fieldnames):
                    issues.append(
                        self._issue(
                            dataset_name=contract.dataset_name,
                            severity="info",
                            issue_type="missing_optional_field",
                            field_name=field_name,
                            message=f"Optional field is missing: {field_name}",
                            recommendation="Optional fields may be omitted, but include them when the fixture needs this signal.",
                        )
                    )
                row_count = sum(1 for _ in reader)
                row_counts[contract.dataset_name] = row_count
                if row_count == 0:
                    issues.append(
                        self._issue(
                            dataset_name=contract.dataset_name,
                            severity="warning",
                            issue_type="empty_csv",
                            field_name=None,
                            message=f"Fixture CSV contains no data rows: {path.name}",
                            recommendation="Add at least one representative row for offline contract testing.",
                        )
                    )
        except csv.Error as exc:
            issues.append(
                self._issue(
                    dataset_name=contract.dataset_name,
                    severity="error",
                    issue_type="csv_read_error",
                    field_name=None,
                    message=f"Could not read fixture CSV {path}: {exc}",
                    recommendation="Fix the CSV formatting and rerun the contract validator.",
                )
            )
        except OSError as exc:
            issues.append(
                self._issue(
                    dataset_name=contract.dataset_name,
                    severity="error",
                    issue_type="csv_read_error",
                    field_name=None,
                    message=f"Could not read fixture CSV {path}: {exc}",
                    recommendation="Check file permissions and rerun the contract validator.",
                )
            )

    def _issue(
        self,
        dataset_name: str,
        severity: str,
        issue_type: str,
        field_name: str | None,
        message: str,
        recommendation: str,
    ) -> ExternalContractValidationIssue:
        return ExternalContractValidationIssue(
            severity=severity,
            source_name=self.source_name,
            dataset_name=dataset_name,
            issue_type=issue_type,
            field_name=field_name,
            message=message,
            recommendation=recommendation,
        )

    def _report(
        self,
        issues: list[ExternalContractValidationIssue],
        row_counts: dict[str, int],
    ) -> ExternalContractValidationReport:
        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        info_count = sum(1 for issue in issues if issue.severity == "info")
        passed = error_count == 0
        summary = (
            f"External adapter contract validation {'passed' if passed else 'failed'}: "
            f"error={error_count}, warning={warning_count}, info={info_count}."
        )
        return ExternalContractValidationReport(
            source_name=self.source_name,
            fixture_dir=str(self.fixture_dir),
            generated_at=datetime.now(),
            total_issues=len(issues),
            error_count=error_count,
            warning_count=warning_count,
            info_count=info_count,
            passed=passed,
            issues=issues,
            row_counts=row_counts,
            summary=summary,
        )
