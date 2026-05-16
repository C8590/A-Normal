from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from ashare_alpha.reports.models import BacktestResearchReport, DailyResearchReport, ReportStockItem


def render_daily_report_markdown(report: DailyResearchReport) -> str:
    lines = [
        "# 每日研究报告",
        "",
        "## 1. 摘要",
        f"- 日期：{report.report_date.isoformat()}",
        f"- 市场状态：{report.market_regime}（评分 {report.market_regime_score:.1f}）",
        f"- 股票总数：{report.total_stocks}",
        f"- 可交易股票数：{report.allowed_universe_count}",
        f"- BUY / WATCH / BLOCK：{report.buy_count} / {report.watch_count} / {report.block_count}",
        f"- 高风险股票数量：{report.high_risk_count}",
        "",
        "## 2. BUY 候选",
    ]
    if not report.buy_candidates:
        lines.extend(["- 当前无 BUY 信号。", ""])
    else:
        lines.extend(_stock_table(report.buy_candidates, include_position=True))

    lines.extend(["## 3. WATCH 观察名单"])
    if report.watch_candidates:
        lines.extend(_stock_table(report.watch_candidates, include_position=False))
    else:
        lines.extend(["- 当前无 WATCH 观察名单。", ""])

    lines.extend(["## 4. BLOCK 禁买 / 剔除股票"])
    if report.blocked_stocks:
        lines.extend(_stock_table(report.blocked_stocks, include_position=False))
    else:
        lines.extend(["- 当前无 BLOCK 或股票池剔除记录。", ""])

    lines.extend(["## 5. 事件风险"])
    if report.recent_event_risk_stocks:
        lines.extend(_event_table(report.recent_event_risk_stocks))
    else:
        lines.extend(["- 近期公告事件未触发明显风险。", ""])

    lines.extend(["## 6. 股票池剔除原因统计"])
    if report.universe_exclude_reason_counts:
        for reason, count in report.universe_exclude_reason_counts.items():
            lines.append(f"- {reason}：{count}")
    else:
        lines.append("- 无股票池剔除原因。")

    lines.extend(
        [
            "",
            "## 7. 当前配置摘要",
            f"- 初始资金：{report.initial_cash:.2f}",
            f"- 最大持仓数：{report.max_positions}",
            f"- 单票最大仓位：{report.max_position_weight:.2%}",
            f"- 交易单位：{report.lot_size} 股",
            f"- 佣金率：{report.commission_rate:.6f}",
            f"- 最低佣金：{report.min_commission:.2f}",
            f"- 卖出印花税率：{report.stamp_tax_rate_on_sell:.6f}",
            f"- 滑点：{report.slippage_bps:.2f} bps",
            "",
            "## 8. 风险提示",
            f"- {report.disclaimer}",
            "",
        ]
    )
    return "\n".join(lines)


def render_backtest_report_markdown(report: BacktestResearchReport) -> str:
    lines = [
        "# 回测研究报告",
        "",
        "## 1. 回测区间",
        f"- 起始日期：{report.start_date.isoformat()}",
        f"- 结束日期：{report.end_date.isoformat()}",
        "",
        "## 2. 核心指标",
        f"- 初始资金：{report.initial_cash:.2f}",
        f"- 期末权益：{report.final_equity:.2f}",
        f"- 总收益率：{report.total_return:.2%}",
        f"- 年化收益率：{report.annualized_return:.2%}",
        f"- 最大回撤：{report.max_drawdown:.2%}",
        f"- Sharpe：{report.sharpe:.4f}",
        f"- 胜率：{report.win_rate:.2%}" if report.win_rate is not None else "- 胜率：无成交",
        f"- 换手率：{report.turnover:.4f}",
        f"- price_source: {report.price_source}",
        f"- execution_price_source: {report.execution_price_source}",
        f"- valuation_price_source: {report.valuation_price_source}",
        f"- adjusted research note: {report.adjusted_research_note}",
        "",
        "## 3. 交易摘要",
        f"- 模拟订单数：{report.trade_count}",
        f"- 成交数：{report.filled_trade_count}",
        f"- 拒绝数：{report.rejected_trade_count}",
        f"- 无成交：{'是' if report.no_trade else '否'}",
    ]
    if report.no_trade_reason:
        lines.append(f"- 无成交说明：{report.no_trade_reason}")

    lines.extend(["", "## 4. 拒绝成交原因"])
    if report.top_reject_reasons:
        for reason, count in report.top_reject_reasons.items():
            lines.append(f"- {reason}：{count}")
    else:
        lines.append("- 无拒绝成交记录。")

    lines.extend(["", "## 5. 标的交易归因"])
    if report.trade_summary_by_symbol:
        lines.extend(
            [
                "| 代码 | 成交次数 | 买入次数 | 卖出次数 | 实现盈亏 | 拒绝次数 |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for item in report.trade_summary_by_symbol:
            lines.append(
                f"| {item.ts_code} | {item.filled_trades} | {item.buy_count} | {item.sell_count} | "
                f"{item.realized_pnl:.2f} | {item.rejected_trades} |"
            )
    else:
        lines.append("- 无标的成交归因。")

    lines.extend(["", "## 6. 最近净值曲线"])
    if report.equity_curve_tail:
        lines.extend(["| 日期 | 现金 | 市值 | 总权益 | 当日收益 | 回撤 |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
        for row in report.equity_curve_tail:
            lines.append(
                f"| {row['trade_date']} | {row['cash']:.2f} | {row['market_value']:.2f} | "
                f"{row['total_equity']:.2f} | {row['daily_return']:.2%} | {row['drawdown']:.2%} |"
            )
    else:
        lines.append("- 无净值曲线记录。")

    lines.extend(
        [
            "",
            "## 7. 配置摘要",
            f"- 初始资金配置：{report.initial_cash_config:.2f}",
            f"- 最大持仓数：{report.max_positions}",
            f"- 单票最大仓位：{report.max_position_weight:.2%}",
            f"- 调仓频率：{report.rebalance_frequency}",
            f"- 执行价格：{report.execution_price}",
            f"- T+1：{'开启' if report.t_plus_one else '关闭'}",
            f"- 交易单位：{report.lot_size} 股",
            f"- 佣金率：{report.commission_rate:.6f}",
            f"- 最低佣金：{report.min_commission:.2f}",
            f"- 卖出印花税率：{report.stamp_tax_rate_on_sell:.6f}",
            f"- 滑点：{report.slippage_bps:.2f} bps",
            "",
            "## 8. 风险提示",
            f"- {report.disclaimer}",
            "- 回测是模拟研究，不是实盘结果；当前系统不会自动下单。",
            "",
        ]
    )
    return "\n".join(lines)


def report_to_json_dict(report: DailyResearchReport | BacktestResearchReport) -> dict[str, Any]:
    payload = report.model_dump() if isinstance(report, BaseModel) else dict(report)
    return _json_ready(payload)


def _stock_table(items: list[ReportStockItem], include_position: bool) -> list[str]:
    if include_position:
        lines = [
            "| 代码 | 名称 | 行业 | 评分 | 风险等级 | 目标仓位 | 目标股数 | 主要理由 |",
            "| --- | --- | --- | ---: | --- | ---: | ---: | --- |",
        ]
        for item in items:
            lines.append(
                f"| {item.ts_code} | {item.name} | {item.industry or '-'} | {item.stock_score:.1f} | "
                f"{item.risk_level} | {item.target_weight:.2%} | {item.target_shares} | {_brief_reason(item)} |"
            )
        lines.append("")
        return lines

    lines = [
        "| 代码 | 名称 | 行业 | 信号 | 评分 | 风险等级 | 主要理由 |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| {item.ts_code} | {item.name} | {item.industry or '-'} | {item.signal} | {item.stock_score:.1f} | "
            f"{item.risk_level} | {_brief_reason(item)} |"
        )
    lines.append("")
    return lines


def _event_table(items: list[ReportStockItem]) -> list[str]:
    lines = [
        "| 代码 | 名称 | 信号 | 事件分 | 事件风险分 | 事件说明 |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for item in items:
        lines.append(
            f"| {item.ts_code} | {item.name} | {item.signal} | {item.event_score or 0:.1f} | "
            f"{item.event_risk_score or 0:.1f} | {_escape_cell(item.event_reason or item.reason)} |"
        )
    lines.append("")
    return lines


def _brief_reason(item: ReportStockItem) -> str:
    parts = [item.reason]
    if item.universe_exclude_reason_text:
        parts.append(f"剔除原因：{item.universe_exclude_reason_text}")
    if item.event_reason and item.signal == "BLOCK":
        parts.append(f"事件说明：{item.event_reason}")
    return _escape_cell("；".join(parts))


def _escape_cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ")


def _json_ready(value: Any) -> Any:
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return _json_ready(value.model_dump())
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value
