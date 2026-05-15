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
                    message="daily_bar 已通过模型校验，包含 trade_date 字段。",
                    recommendation="继续保留 trade_date 校验作为行情可见性基础。",
                )
            )
        if financial_summary:
            issues.append(
                LeakageIssue(
                    severity="info",
                    issue_type="financial_publish_date_present",
                    dataset_name="financial_summary",
                    message="financial_summary 已通过模型校验，包含 publish_date 字段。",
                    recommendation="特征构造时应使用 publish_date，而不是 report_date 判断可见性。",
                )
            )
        if announcement_events:
            issues.append(
                LeakageIssue(
                    severity="info",
                    issue_type="announcement_event_time_present",
                    dataset_name="announcement_event",
                    message="announcement_event 已通过模型校验，包含 event_time 字段。",
                    recommendation="事件特征构造时应使用 event_time 判断可见性。",
                )
            )


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
