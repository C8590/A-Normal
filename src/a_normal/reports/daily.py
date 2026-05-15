from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from a_normal.config import load_config
from a_normal.data import DataAdapter, LocalCsvAdapter, StockMaster
from a_normal.data.models import _validate_date_format
from a_normal.factors import EventScoreResult, build_factor_daily, load_factors_config, score_announcement_events
from a_normal.signals import SignalDaily, build_signals, load_scoring_config
from a_normal.universe import UniverseDaily, build_universe_daily, load_universe_config


RISK_DISCLOSURE = "风险提示：本报告不是投资建议，不保证收益。"


class DailyReportRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ts_code: str
    name: str
    stock_score: float = Field(ge=0, le=100)
    signal: str
    target_weight: float = Field(ge=0, le=1)
    positive_reasons: tuple[str, ...] = Field(default_factory=tuple)
    risk_reasons: tuple[str, ...] = Field(default_factory=tuple)


class DailyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    report_date: date
    market_regime: str
    total_position_advice: float = Field(ge=0, le=1)
    candidates_top20: tuple[DailyReportRow, ...] = Field(default_factory=tuple)
    blocked_stocks: tuple[DailyReportRow, ...] = Field(default_factory=tuple)
    config_summary: dict[str, Any] = Field(default_factory=dict)
    risk_disclosure: str = RISK_DISCLOSURE

    @field_validator("report_date", mode="before")
    @classmethod
    def validate_report_date(cls, value: Any) -> Any:
        return _validate_date_format(value)


def generate_daily_report(
    as_of_date: str | date,
    market_regime: str = "normal",
    adapter: DataAdapter | None = None,
    config_dir: str | Path | None = None,
) -> DailyReport:
    data_adapter = adapter or LocalCsvAdapter()
    universe_config = load_universe_config(config_dir)
    scoring_config = load_scoring_config(config_dir)
    universe_result = build_universe_daily(as_of_date, adapter=data_adapter, config=universe_config)
    daily_bars = data_adapter.load_daily_bars()
    factor_rows = build_factor_daily(daily_bars, as_of_date=as_of_date)
    event_rows = score_announcement_events(data_adapter.load_announcement_events(), as_of_date=as_of_date)
    signals = build_signals(
        list(universe_result.rows),
        factor_rows,
        event_rows,
        market_regime=market_regime,
        as_of_date=as_of_date,
        config=scoring_config,
    )
    return build_daily_report(
        as_of_date=as_of_date,
        market_regime=market_regime,
        stock_master=data_adapter.load_stock_master(),
        signals=signals,
        universe_daily=list(universe_result.rows),
        event_scores=event_rows,
        config_summary=_config_summary(config_dir),
    )


def build_daily_report(
    as_of_date: str | date,
    market_regime: str,
    stock_master: list[StockMaster],
    signals: list[SignalDaily],
    universe_daily: list[UniverseDaily],
    event_scores: list[EventScoreResult],
    config_summary: dict[str, Any] | None = None,
) -> DailyReport:
    target_date = _parse_date(as_of_date)
    names = {item.stock_code: item.stock_name for item in stock_master}
    universe_by_code = {item.ts_code: item for item in universe_daily}
    event_by_code = _latest_event_by_code(event_scores)

    rows = []
    for signal in sorted(signals, key=lambda item: (-item.stock_score, item.ts_code)):
        universe = universe_by_code.get(signal.ts_code)
        event = event_by_code.get(signal.ts_code)
        rows.append(
            DailyReportRow(
                ts_code=signal.ts_code,
                name=names.get(signal.ts_code, ""),
                stock_score=signal.stock_score,
                signal=signal.signal,
                target_weight=signal.target_weight,
                positive_reasons=tuple(_positive_reasons(signal, event)),
                risk_reasons=tuple(_risk_reasons(signal, universe, event)),
            )
        )

    candidates = tuple(row for row in rows if row.signal != "BLOCK")[:20]
    blocked = tuple(row for row in rows if row.signal == "BLOCK")
    total_position = round(min(1.0, sum(row.target_weight for row in candidates if row.signal in {"BUY", "HOLD"})), 6)

    return DailyReport(
        report_date=target_date,
        market_regime=market_regime,
        total_position_advice=total_position,
        candidates_top20=candidates,
        blocked_stocks=blocked,
        config_summary=config_summary or {},
    )


def save_daily_report(report: DailyReport, output_dir: str | Path) -> dict[str, Path]:
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    date_text = report.report_date.isoformat()
    markdown_path = base_dir / f"daily_report_{date_text}.md"
    csv_path = base_dir / f"daily_report_{date_text}.csv"
    json_path = base_dir / f"daily_report_{date_text}.json"

    markdown_path.write_text(_to_markdown(report), encoding="utf-8")
    _write_csv(report, csv_path)
    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"markdown": markdown_path, "csv": csv_path, "json": json_path}


def _to_markdown(report: DailyReport) -> str:
    lines = [
        f"# 每日报告 {report.report_date.isoformat()}",
        "",
        f"- 日期：{report.report_date.isoformat()}",
        f"- 市场状态：{report.market_regime}",
        f"- 总仓位建议：{report.total_position_advice:.2%}",
        "",
        "## 候选股票 Top 20",
        "",
    ]
    if report.candidates_top20:
        lines.extend(
            [
                "| 股票代码 | 名称 | 综合评分 | 信号 | 目标仓位 | 主要加分原因 | 主要风险原因 |",
                "| --- | --- | ---: | --- | ---: | --- | --- |",
            ]
        )
        for row in report.candidates_top20:
            lines.append(_markdown_row(row))
    else:
        lines.append("暂无候选股票。")

    lines.extend(["", "## 禁买股票", ""])
    if report.blocked_stocks:
        lines.extend(["| 股票代码 | 名称 | 综合评分 | 禁买原因 |", "| --- | --- | ---: | --- |"])
        for row in report.blocked_stocks:
            risk = "；".join(row.risk_reasons) or "信号为 BLOCK"
            lines.append(f"| {row.ts_code} | {row.name} | {row.stock_score:.2f} | {risk} |")
    else:
        lines.append("暂无禁买股票。")

    lines.extend(["", "## 当前配置摘要", ""])
    lines.append("```json")
    lines.append(json.dumps(report.config_summary, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.extend(["", f"## 风险提示", "", report.risk_disclosure, ""])
    return "\n".join(lines)


def _write_csv(report: DailyReport, path: Path) -> None:
    fields = [
        "section",
        "report_date",
        "market_regime",
        "ts_code",
        "name",
        "stock_score",
        "signal",
        "target_weight",
        "positive_reasons",
        "risk_reasons",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for section, rows in (("candidate", report.candidates_top20), ("blocked", report.blocked_stocks)):
            for row in rows:
                writer.writerow(
                    {
                        "section": section,
                        "report_date": report.report_date.isoformat(),
                        "market_regime": report.market_regime,
                        "ts_code": row.ts_code,
                        "name": row.name,
                        "stock_score": row.stock_score,
                        "signal": row.signal,
                        "target_weight": row.target_weight,
                        "positive_reasons": "；".join(row.positive_reasons),
                        "risk_reasons": "；".join(row.risk_reasons),
                    }
                )


def _markdown_row(row: DailyReportRow) -> str:
    positive = "；".join(row.positive_reasons) or "无"
    risk = "；".join(row.risk_reasons) or "无"
    return (
        f"| {row.ts_code} | {row.name} | {row.stock_score:.2f} | {row.signal} | "
        f"{row.target_weight:.2%} | {positive} | {risk} |"
    )


def _positive_reasons(signal: SignalDaily, event: EventScoreResult | None) -> list[str]:
    reasons = []
    if signal.stock_score >= 70:
        reasons.append("综合评分较高")
    elif signal.stock_score >= 55:
        reasons.append("综合评分中等偏上")
    if signal.target_weight > 0:
        reasons.append(f"建议仓位{signal.target_weight:.2%}")
    if event is not None and event.event_score > 0:
        reasons.append(f"公告正向：{event.event_type}")
    if signal.signal in {"BUY", "HOLD", "WATCH"}:
        reasons.append(f"信号为{signal.signal}")
    return reasons


def _risk_reasons(
    signal: SignalDaily,
    universe: UniverseDaily | None,
    event: EventScoreResult | None,
) -> list[str]:
    reasons = []
    if universe is not None and not universe.is_allowed:
        reasons.append(f"股票池排除：{','.join(universe.exclude_reasons)}")
    if signal.risk_level == "high":
        reasons.append("风险等级高")
    elif signal.risk_level == "medium":
        reasons.append("风险等级中")
    if event is not None:
        if event.event_risk_score >= 0.4:
            reasons.append(f"公告风险：{event.event_type}")
        if event.event_block_buy:
            reasons.append("公告触发禁买")
    if signal.signal in {"SELL", "BLOCK"}:
        reasons.append(f"信号为{signal.signal}")
    if signal.target_weight == 0 and signal.signal in {"BUY", "HOLD"}:
        reasons.append("目标仓位为0")
    return reasons


def _latest_event_by_code(event_scores: list[EventScoreResult]) -> dict[str, EventScoreResult]:
    result: dict[str, EventScoreResult] = {}
    for event in event_scores:
        current = result.get(event.stock_code)
        if current is None or event.event_date > current.event_date:
            result[event.stock_code] = event
    return result


def _config_summary(config_dir: str | Path | None) -> dict[str, Any]:
    app_config = load_config(config_dir)
    scoring_config = load_scoring_config(config_dir)
    universe_config = load_universe_config(config_dir)
    factors_config = load_factors_config(config_dir)
    return {
        "trading_rules": app_config.trading_rules.model_dump(mode="json"),
        "fees": app_config.fees.model_dump(mode="json"),
        "universe": universe_config.model_dump(mode="json"),
        "scoring": scoring_config.model_dump(mode="json"),
        "factors": factors_config.model_dump(mode="json"),
    }


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    _validate_date_format(value)
    return date.fromisoformat(value)
