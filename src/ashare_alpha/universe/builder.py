from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import AnnouncementEvent, DailyBar, FinancialSummary, StockMaster
from ashare_alpha.universe.models import UniverseDailyRecord
from ashare_alpha.universe.reasons import ExcludeReason, join_reason_text


NEGATIVE_EVENT_TYPES = {
    "shareholder_reduce",
    "regulatory_penalty",
    "investigation",
    "litigation",
    "earnings_negative",
}


class UniverseBuilder:
    def __init__(
        self,
        config: ProjectConfig,
        stock_master: list[StockMaster],
        daily_bars: list[DailyBar],
        financial_summary: list[FinancialSummary] | None = None,
        announcement_events: list[AnnouncementEvent] | None = None,
    ) -> None:
        self.config = config
        self.stock_master = stock_master
        self.financial_summary = financial_summary or []
        self.announcement_events = announcement_events or []
        self._bars_by_code = _group_daily_bars(daily_bars)
        self._events_by_code = _group_events(self.announcement_events)

    def build_for_date(self, trade_date: date) -> list[UniverseDailyRecord]:
        records = [self._build_stock_record(stock, trade_date) for stock in sorted(self.stock_master, key=lambda s: s.ts_code)]
        return records

    def _build_stock_record(self, stock: StockMaster, trade_date: date) -> UniverseDailyRecord:
        reasons: list[ExcludeReason] = []
        universe_config = self.config.universe
        trading_rules = self.config.trading_rules
        window = self.config.factors.liquidity_window or 20
        bars = [bar for bar in self._bars_by_code.get(stock.ts_code, []) if bar.trade_date <= trade_date]
        latest_bar = next((bar for bar in reversed(bars) if bar.trade_date == trade_date), None)
        recent_bars = bars[-window:]

        listing_days = (trade_date - stock.list_date).days
        avg_amount = _average_amount(recent_bars) if len(recent_bars) >= window else None
        latest_close = latest_bar.close if latest_bar is not None else None
        one_lot_value = latest_close * trading_rules.lot_size if latest_close is not None else None
        recent_negative_events = self._recent_negative_events(stock.ts_code, trade_date)

        if stock.board not in universe_config.allowed_boards:
            reasons.append(ExcludeReason.BOARD_NOT_ALLOWED)
        if stock.board in universe_config.excluded_boards:
            reasons.append(ExcludeReason.BOARD_EXCLUDED)
        if universe_config.exclude_st and stock.is_st:
            reasons.append(ExcludeReason.IS_ST)
        if universe_config.exclude_star_st and stock.is_star_st:
            reasons.append(ExcludeReason.IS_STAR_ST)
        if universe_config.exclude_delisting_risk and stock.is_delisting_risk:
            reasons.append(ExcludeReason.DELISTING_RISK)
        if universe_config.exclude_suspended and stock.is_suspended:
            reasons.append(ExcludeReason.SUSPENDED)
        if listing_days < universe_config.min_listing_days:
            reasons.append(ExcludeReason.LISTING_DAYS_TOO_SHORT)
        if latest_bar is None:
            reasons.append(ExcludeReason.MISSING_LATEST_BAR)
        elif universe_config.exclude_suspended and not latest_bar.is_trading:
            reasons.append(ExcludeReason.NOT_TRADING_ON_DATE)
        if len(recent_bars) < window:
            reasons.append(ExcludeReason.INSUFFICIENT_DAILY_BARS)
        if avg_amount is not None and avg_amount < universe_config.min_avg_amount_20d:
            reasons.append(ExcludeReason.LOW_AVG_AMOUNT_20D)
        if one_lot_value is not None and one_lot_value > _max_one_lot_value(self.config):
            reasons.append(ExcludeReason.TOO_EXPENSIVE_FOR_CAPITAL)
        if universe_config.block_recent_negative_events and recent_negative_events:
            reasons.append(ExcludeReason.RECENT_NEGATIVE_EVENT)

        unique_reasons = _deduplicate_reasons(reasons)
        risk_score = _risk_score(stock, unique_reasons, recent_negative_events)
        return UniverseDailyRecord(
            trade_date=trade_date,
            ts_code=stock.ts_code,
            symbol=stock.symbol,
            name=stock.name,
            exchange=stock.exchange,
            board=stock.board,
            industry=stock.industry,
            is_allowed=not unique_reasons,
            exclude_reasons=[reason.value for reason in unique_reasons],
            exclude_reason_text=join_reason_text(unique_reasons),
            listing_days=listing_days,
            latest_close=latest_close,
            one_lot_value=one_lot_value,
            avg_amount_20d=avg_amount,
            trading_days_20d=sum(1 for bar in recent_bars if bar.is_trading),
            liquidity_score=_liquidity_score(avg_amount, universe_config.min_avg_amount_20d),
            risk_score=risk_score,
            has_recent_negative_event=bool(recent_negative_events),
            recent_negative_event_count=len(recent_negative_events),
            latest_negative_event_title=recent_negative_events[-1].title if recent_negative_events else None,
        )

    def _recent_negative_events(self, ts_code: str, trade_date: date) -> list[AnnouncementEvent]:
        end_time = datetime.combine(trade_date, time.max)
        start_time = end_time - timedelta(days=self.config.universe.recent_event_window_days)
        events = [
            event
            for event in self._events_by_code.get(ts_code, [])
            if start_time <= event.event_time <= end_time and _is_negative_event(event)
        ]
        return sorted(events, key=lambda event: event.event_time)


def save_universe_csv(records: list[UniverseDailyRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(UniverseDailyRecord.model_fields)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            row["exclude_reasons"] = ",".join(record.exclude_reasons)
            writer.writerow(row)


def summarize_universe(records: list[UniverseDailyRecord]) -> dict:
    reason_counts: Counter[str] = Counter()
    for record in records:
        reason_counts.update(record.exclude_reasons)
    return {
        "total": len(records),
        "allowed": sum(1 for record in records if record.is_allowed),
        "excluded": sum(1 for record in records if not record.is_allowed),
        "reason_counts": dict(sorted(reason_counts.items())),
    }


def _group_daily_bars(daily_bars: list[DailyBar]) -> dict[str, list[DailyBar]]:
    grouped: dict[str, list[DailyBar]] = defaultdict(list)
    for bar in daily_bars:
        grouped[bar.ts_code].append(bar)
    for rows in grouped.values():
        rows.sort(key=lambda bar: bar.trade_date)
    return grouped


def _group_events(events: list[AnnouncementEvent]) -> dict[str, list[AnnouncementEvent]]:
    grouped: dict[str, list[AnnouncementEvent]] = defaultdict(list)
    for event in events:
        grouped[event.ts_code].append(event)
    for rows in grouped.values():
        rows.sort(key=lambda event: event.event_time)
    return grouped


def _deduplicate_reasons(reasons: list[ExcludeReason]) -> list[ExcludeReason]:
    seen: set[ExcludeReason] = set()
    result: list[ExcludeReason] = []
    for reason in reasons:
        if reason not in seen:
            result.append(reason)
            seen.add(reason)
    return result


def _average_amount(bars: list[DailyBar]) -> float:
    return round(sum(bar.amount for bar in bars) / len(bars), 6)


def _liquidity_score(avg_amount: float | None, min_avg_amount: float) -> float:
    if avg_amount is None:
        return 0.0
    if avg_amount >= 100_000_000:
        return 100.0
    if avg_amount >= 50_000_000:
        return 80.0
    if avg_amount >= min_avg_amount:
        return 60.0
    return 30.0


def _risk_score(stock: StockMaster, reasons: list[ExcludeReason], recent_negative_events: list[AnnouncementEvent]) -> float:
    score = 0.0
    if stock.is_st:
        score += 40
    if stock.is_star_st:
        score += 60
    if stock.is_delisting_risk:
        score += 60
    if ExcludeReason.SUSPENDED in reasons or ExcludeReason.NOT_TRADING_ON_DATE in reasons:
        score += 30
    if ExcludeReason.LISTING_DAYS_TOO_SHORT in reasons:
        score += 20
    if ExcludeReason.LOW_AVG_AMOUNT_20D in reasons:
        score += 20
    if ExcludeReason.RECENT_NEGATIVE_EVENT in reasons:
        score += 40
    if ExcludeReason.TOO_EXPENSIVE_FOR_CAPITAL in reasons:
        score += 15
    score += 20 * sum(1 for event in recent_negative_events if event.event_risk_level == "high")
    return min(100.0, score)


def _max_one_lot_value(config: ProjectConfig) -> float:
    return config.universe.initial_cash_for_affordability * config.universe.max_one_lot_position_pct


def _is_negative_event(event: AnnouncementEvent) -> bool:
    return (
        event.event_direction == "negative"
        or event.event_risk_level == "high"
        or event.event_type in NEGATIVE_EVENT_TYPES
    )
