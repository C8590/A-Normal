from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from ashare_alpha.audit.models import LeakageAuditReport, LeakageIssue
from ashare_alpha.audit.point_in_time import (
    infer_available_at_for_announcement_event,
    infer_available_at_for_daily_bar,
    infer_available_at_for_financial_summary,
    make_decision_time,
)
from ashare_alpha.data import AnnouncementEvent, DailyBar, FinancialSummary, LocalCsvAdapter, StockMaster
from ashare_alpha.data.realism import OptionalRealismDataLoader, RealismDataBundle
from ashare_alpha.data.realism.models import AdjustmentFactorRecord, CorporateActionRecord, StockStatusHistoryRecord
from ashare_alpha.data.validation import DataValidationError


class LeakageAuditor:
    def __init__(
        self,
        data_dir: Path,
        config_dir: Path,
        source_name: str = "local_csv",
        data_version: str = "sample",
    ) -> None:
        self.data_dir = data_dir
        self.config_dir = config_dir
        self.source_name = source_name
        self.data_version = data_version

    def audit_for_date(self, trade_date: date) -> LeakageAuditReport:
        stock_master, daily_bars, financial_summary, announcement_events = self._load_data()
        return self.audit_records(
            audit_date=trade_date,
            start_date=None,
            end_date=None,
            stock_master=stock_master,
            daily_bars=daily_bars,
            financial_summary=financial_summary,
            announcement_events=announcement_events,
        )

    def audit_for_range(self, start_date: date, end_date: date) -> LeakageAuditReport:
        if start_date >= end_date:
            raise ValueError("start_date must be earlier than end_date")
        stock_master, daily_bars, financial_summary, announcement_events = self._load_data()
        return self.audit_records(
            audit_date=None,
            start_date=start_date,
            end_date=end_date,
            stock_master=stock_master,
            daily_bars=daily_bars,
            financial_summary=financial_summary,
            announcement_events=announcement_events,
        )

    def audit_records(
        self,
        audit_date: date | None,
        start_date: date | None,
        end_date: date | None,
        stock_master: list[StockMaster],
        daily_bars: list[DailyBar],
        financial_summary: list[FinancialSummary],
        announcement_events: list[AnnouncementEvent],
    ) -> LeakageAuditReport:
        issues: list[LeakageIssue] = []
        trade_dates = _audit_trade_dates(audit_date, start_date, end_date, daily_bars)
        self._audit_source_version(issues)
        self._audit_stock_master(stock_master, issues, audit_date, start_date, end_date)
        self._audit_financial_summary(financial_summary, issues, trade_dates)
        self._audit_announcement_events(announcement_events, issues, trade_dates)
        self._audit_daily_bars(daily_bars, issues, trade_dates)
        realism_bundle = self._load_realism_bundle(issues)
        if realism_bundle is not None:
            self._audit_realism_data(realism_bundle, issues, trade_dates)
        self._audit_coverage(daily_bars, financial_summary, announcement_events, issues)
        return _report(
            audit_date=audit_date,
            start_date=start_date,
            end_date=end_date,
            data_dir=self.data_dir,
            config_dir=self.config_dir,
            source_name=self.source_name,
            data_version=self.data_version,
            issues=issues,
        )

    def _load_data(self) -> tuple[
        list[StockMaster],
        list[DailyBar],
        list[FinancialSummary],
        list[AnnouncementEvent],
    ]:
        adapter = LocalCsvAdapter(self.data_dir)
        return (
            adapter.load_stock_master(),
            adapter.load_daily_bars(),
            adapter.load_financial_summary(),
            adapter.load_announcement_events(),
        )

    def _load_realism_bundle(self, issues: list[LeakageIssue]) -> RealismDataBundle | None:
        try:
            return OptionalRealismDataLoader(self.data_dir).load_all()
        except DataValidationError as exc:
            issues.append(
                LeakageIssue(
                    severity="warning",
                    issue_type="realism_validation_error",
                    dataset_name="realism",
                    message=str(exc),
                    recommendation="Fix optional realism CSV validation before relying on point-in-time realism audits.",
                )
            )
            return None

    def _audit_source_version(self, issues: list[LeakageIssue]) -> None:
        if not self.source_name:
            issues.append(
                LeakageIssue(
                    severity="error",
                    issue_type="missing_source_name",
                    dataset_name="metadata",
                    message="source_name 为空，无法追踪数据来源。",
                    recommendation="为审计任务提供非空 source_name。",
                )
            )
        if not self.data_version:
            issues.append(
                LeakageIssue(
                    severity="warning",
                    issue_type="missing_data_version",
                    dataset_name="metadata",
                    message="data_version 为空，无法追踪数据版本或导入批次。",
                    recommendation="为每次导入或样例数据设置稳定 data_version。",
                )
            )

    def _audit_stock_master(
        self,
        stock_master: list[StockMaster],
        issues: list[LeakageIssue],
        audit_date: date | None,
        start_date: date | None,
        end_date: date | None,
    ) -> None:
        if not stock_master:
            return
        issues.append(
            LeakageIssue(
                severity="warning",
                issue_type="stock_master_current_state_risk",
                dataset_name="stock_master",
                trade_date=audit_date,
                data_date=end_date or audit_date or start_date,
                message=(
                    "stock_master 中 board、industry、ST、停牌、退市风险等当前状态字段"
                    "可能不具备历史时点信息。"
                ),
                recommendation="真实数据接入后应使用带 effective_date 的历史状态表，并按 trade_date 做 point-in-time 查询。",
            )
        )

    def _audit_financial_summary(
        self,
        records: list[FinancialSummary],
        issues: list[LeakageIssue],
        trade_dates: list[date],
    ) -> None:
        for item in records:
            available_at = infer_available_at_for_financial_summary(item)
            if item.publish_date < item.report_date:
                issues.append(
                    LeakageIssue(
                        severity="error",
                        issue_type="financial_publish_before_report",
                        dataset_name="financial_summary",
                        ts_code=item.ts_code,
                        data_date=item.report_date,
                        available_at=available_at,
                        message="财务数据披露日期早于报告期日期，疑似数据错误。",
                        recommendation="检查原始财务数据的 report_date 和 publish_date。",
                    )
                )
            for trade_date in trade_dates:
                if item.report_date <= trade_date < item.publish_date:
                    issues.append(
                        LeakageIssue(
                            severity="warning",
                            issue_type="financial_not_yet_available",
                            dataset_name="financial_summary",
                            ts_code=item.ts_code,
                            trade_date=trade_date,
                            data_date=item.report_date,
                            available_at=available_at,
                            message="该财务报告期在研究日已结束，但披露日仍在未来，不能作为当日特征使用。",
                            recommendation="按 publish_date/available_at 过滤财务特征，避免使用未披露数据。",
                        )
                    )

    def _audit_announcement_events(
        self,
        records: list[AnnouncementEvent],
        issues: list[LeakageIssue],
        trade_dates: list[date],
    ) -> None:
        for event in records:
            available_at = infer_available_at_for_announcement_event(event)
            for trade_date in trade_dates:
                if event.event_time.date() > trade_date:
                    issues.append(
                        LeakageIssue(
                            severity="info",
                            issue_type="announcement_future_event",
                            dataset_name="announcement_event",
                            ts_code=event.ts_code,
                            trade_date=trade_date,
                            data_date=event.event_time.date(),
                            available_at=available_at,
                            message="该公告发生在研究日之后，不能在该研究日使用。",
                            recommendation="按 event_time/available_at 过滤公告事件特征。",
                        )
                    )

    def _audit_daily_bars(
        self,
        records: list[DailyBar],
        issues: list[LeakageIssue],
        trade_dates: list[date],
    ) -> None:
        if not records:
            return
        if trade_dates:
            issues.append(
                LeakageIssue(
                    severity="info",
                    issue_type="daily_bar_after_close_rule",
                    dataset_name="daily_bar",
                    trade_date=trade_dates[-1],
                    data_date=trade_dates[-1],
                    available_at=make_decision_time(trade_dates[-1], "after_close"),
                    message="日线默认在 trade_date 15:30 后完整可见，after_close 日频决策可以使用当天日线。",
                    recommendation="如未来实现盘中策略，应单独使用分钟级或盘中可见性规则。",
                )
            )
        for bar in records:
            infer_available_at_for_daily_bar(bar)

    def _audit_coverage(
        self,
        daily_bars: list[DailyBar],
        financial_summary: list[FinancialSummary],
        announcement_events: list[AnnouncementEvent],
        issues: list[LeakageIssue],
    ) -> None:
        if daily_bars:
            issues.append(
                LeakageIssue(
                    severity="info",
                    issue_type="daily_bar_trade_date_present",
                    dataset_name="daily_bar",
                    message="daily_bar includes trade_date for point-in-time checks.",
                    recommendation="Keep trade_date validation as the market-data visibility baseline.",
                )
            )
        if financial_summary:
            issues.append(
                LeakageIssue(
                    severity="info",
                    issue_type="financial_publish_date_present",
                    dataset_name="financial_summary",
                    message="financial_summary includes publish_date for point-in-time checks.",
                    recommendation="Use publish_date rather than report_date when deciding financial data visibility.",
                )
            )
        if announcement_events:
            issues.append(
                LeakageIssue(
                    severity="info",
                    issue_type="announcement_event_time_present",
                    dataset_name="announcement_event",
                    message="announcement_event includes event_time for point-in-time checks.",
                    recommendation="Use event_time when deciding announcement event visibility.",
                )
            )

    def _audit_realism_data(
        self,
        bundle: RealismDataBundle,
        issues: list[LeakageIssue],
        trade_dates: list[date],
    ) -> None:
        self._audit_stock_status_history_realism(bundle.stock_status_history, issues, trade_dates)
        self._audit_adjustment_factors_realism(bundle.adjustment_factors, issues, trade_dates)
        self._audit_corporate_actions_realism(bundle.corporate_actions, issues, trade_dates)

    def _audit_stock_status_history_realism(
        self,
        records: list[StockStatusHistoryRecord],
        issues: list[LeakageIssue],
        trade_dates: list[date],
    ) -> None:
        for record in records:
            if record.available_at is None:
                issues.append(
                    LeakageIssue(
                        severity="warning",
                        issue_type="stock_status_missing_available_at",
                        dataset_name="stock_status_history",
                        ts_code=record.ts_code,
                        data_date=record.effective_start,
                        message="stock_status_history available_at is missing.",
                        recommendation="Populate available_at so historical status is point-in-time auditable.",
                    )
                )
                continue
            for trade_date in trade_dates:
                if not _status_effective_on(record, trade_date):
                    continue
                decision_time = make_decision_time(trade_date, "after_close")
                if record.available_at > decision_time:
                    issues.append(
                        LeakageIssue(
                            severity="warning",
                            issue_type="stock_status_not_yet_available",
                            dataset_name="stock_status_history",
                            ts_code=record.ts_code,
                            trade_date=trade_date,
                            data_date=record.effective_start,
                            available_at=record.available_at,
                            message="stock status history row is not visible at the decision time.",
                            recommendation="Filter status history by available_at before using it in decisions.",
                        )
                    )

    def _audit_adjustment_factors_realism(
        self,
        records: list[AdjustmentFactorRecord],
        issues: list[LeakageIssue],
        trade_dates: list[date],
    ) -> None:
        for record in records:
            if record.available_at is None:
                issues.append(
                    LeakageIssue(
                        severity="warning",
                        issue_type="adjustment_factor_missing_available_at",
                        dataset_name="adjustment_factor",
                        ts_code=record.ts_code,
                        data_date=record.trade_date,
                        message="adjustment_factor available_at is missing.",
                        recommendation="Populate available_at so adjustment factors are point-in-time auditable.",
                    )
                )
                continue
            for trade_date in trade_dates:
                if record.trade_date > trade_date:
                    continue
                decision_time = make_decision_time(trade_date, "after_close")
                if record.available_at > decision_time:
                    issues.append(
                        LeakageIssue(
                            severity="warning",
                            issue_type="adjustment_factor_not_yet_available",
                            dataset_name="adjustment_factor",
                            ts_code=record.ts_code,
                            trade_date=trade_date,
                            data_date=record.trade_date,
                            available_at=record.available_at,
                            message="adjustment factor row is not visible at the decision time.",
                            recommendation="Filter adjustment factors by available_at before adjusted-price research.",
                        )
                    )
                    break

    def _audit_corporate_actions_realism(
        self,
        records: list[CorporateActionRecord],
        issues: list[LeakageIssue],
        trade_dates: list[date],
    ) -> None:
        for record in records:
            visible_at = record.available_at
            if visible_at is None and record.publish_date is not None:
                visible_at = datetime.combine(record.publish_date, datetime.min.time())
            if visible_at is None:
                issues.append(
                    LeakageIssue(
                        severity="warning",
                        issue_type="corporate_action_missing_visible_time",
                        dataset_name="corporate_action",
                        ts_code=record.ts_code,
                        data_date=record.action_date,
                        message="corporate_action has neither available_at nor publish_date.",
                        recommendation="Populate available_at or publish_date before using corporate actions in research.",
                    )
                )
                continue
            for trade_date in trade_dates:
                if record.action_date > trade_date:
                    continue
                decision_time = make_decision_time(trade_date, "after_close")
                if visible_at > decision_time:
                    issues.append(
                        LeakageIssue(
                            severity="warning",
                            issue_type="corporate_action_not_yet_available",
                            dataset_name="corporate_action",
                            ts_code=record.ts_code,
                            trade_date=trade_date,
                            data_date=record.action_date,
                            available_at=visible_at,
                            message="corporate action row is not visible at the decision time.",
                            recommendation="Filter corporate actions by available_at or publish_date.",
                        )
                    )
                    break

def _audit_trade_dates(
    audit_date: date | None,
    start_date: date | None,
    end_date: date | None,
    daily_bars: list[DailyBar],
) -> list[date]:
    if audit_date is not None:
        return [audit_date]
    if start_date is None or end_date is None:
        return []
    return sorted({bar.trade_date for bar in daily_bars if start_date <= bar.trade_date <= end_date})


def _status_effective_on(record: StockStatusHistoryRecord, trade_date: date) -> bool:
    return record.effective_start <= trade_date and (record.effective_end is None or trade_date <= record.effective_end)


def _report(
    audit_date: date | None,
    start_date: date | None,
    end_date: date | None,
    data_dir: Path,
    config_dir: Path,
    source_name: str,
    data_version: str,
    issues: list[LeakageIssue],
) -> LeakageAuditReport:
    error_count = sum(1 for issue in issues if issue.severity == "error")
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    info_count = sum(1 for issue in issues if issue.severity == "info")
    summary = (
        f"审计完成：error={error_count}, warning={warning_count}, info={info_count}。"
        "审计只检查可见性和常见未来函数风险，不代表数据完全无误。"
    )
    return LeakageAuditReport(
        audit_date=audit_date,
        start_date=start_date,
        end_date=end_date,
        generated_at=datetime.now(),
        data_dir=str(data_dir),
        config_dir=str(config_dir),
        source_name=source_name,
        data_version=data_version,
        total_issues=len(issues),
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        issues=issues,
        passed=error_count == 0,
        summary=summary,
    )


def issue_to_summary(issue: LeakageIssue) -> dict[str, Any]:
    return {
        "severity": issue.severity,
        "issue_type": issue.issue_type,
        "dataset_name": issue.dataset_name,
        "ts_code": issue.ts_code,
        "trade_date": issue.trade_date.isoformat() if issue.trade_date else None,
        "data_date": issue.data_date.isoformat() if issue.data_date else None,
        "message": issue.message,
    }
