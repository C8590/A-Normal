from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from ashare_alpha.config import ProjectConfig
from ashare_alpha.data import AnnouncementEvent, StockMaster
from ashare_alpha.events.models import EventDailyRecord, EventScoreRecord
from ashare_alpha.events.rules import clamp
from ashare_alpha.events.scoring import score_event


class EventFeatureBuilder:
    def __init__(
        self,
        config: ProjectConfig,
        announcement_events: list[AnnouncementEvent],
        stock_master: list[StockMaster] | None = None,
    ) -> None:
        self.config = config
        self.stock_master = stock_master
        self._events_by_code = _group_events(announcement_events)

    def build_for_date(self, trade_date: date) -> list[EventDailyRecord]:
        return [self._build_record(ts_code, trade_date) for ts_code in sorted(self._target_codes())]

    def _target_codes(self) -> set[str]:
        if self.stock_master is not None:
            return {stock.ts_code for stock in self.stock_master}
        return set(self._events_by_code)

    def _build_record(self, ts_code: str, trade_date: date) -> EventDailyRecord:
        scored_events: list[EventScoreRecord] = []
        for event in self._events_by_code.get(ts_code, []):
            try:
                scored = score_event(event, trade_date, self.config)
            except ValueError:
                continue
            if scored is not None:
                scored_events.append(scored)

        if not scored_events:
            return EventDailyRecord(
                trade_date=trade_date,
                ts_code=ts_code,
                event_score=0,
                event_risk_score=0,
                event_count=0,
                positive_event_count=0,
                negative_event_count=0,
                high_risk_event_count=0,
                event_block_buy=False,
                block_buy_reasons=[],
                latest_event_title=None,
                latest_negative_event_title=None,
                event_reason="近窗口内无有效公告事件",
            )

        event_score = clamp(sum(event.signed_event_score for event in scored_events), -100, 100)
        event_risk_score = max(event.risk_score for event in scored_events)
        block_buy_reasons = [event.event_reason for event in scored_events if event.event_block_buy]
        latest_event = max(scored_events, key=lambda event: event.event_time)
        negative_events = [event for event in scored_events if event.signed_event_score < 0]
        latest_negative_event = max(negative_events, key=lambda event: event.event_time) if negative_events else None
        event_block_buy = bool(block_buy_reasons)

        return EventDailyRecord(
            trade_date=trade_date,
            ts_code=ts_code,
            event_score=event_score,
            event_risk_score=event_risk_score,
            event_count=len(scored_events),
            positive_event_count=sum(1 for event in scored_events if event.signed_event_score > 0),
            negative_event_count=len(negative_events),
            high_risk_event_count=sum(
                1 for event in scored_events if event.risk_score >= 60 or event.event_risk_level == "high"
            ),
            event_block_buy=event_block_buy,
            block_buy_reasons=block_buy_reasons,
            latest_event_title=latest_event.title,
            latest_negative_event_title=latest_negative_event.title if latest_negative_event is not None else None,
            event_reason=_aggregate_reason(scored_events, event_score, event_risk_score, block_buy_reasons),
        )


def summarize_event_daily(records: list[EventDailyRecord]) -> dict:
    return {
        "total": len(records),
        "with_events": sum(1 for record in records if record.event_count > 0),
        "block_buy": sum(1 for record in records if record.event_block_buy),
        "positive_events": sum(record.positive_event_count for record in records),
        "negative_events": sum(record.negative_event_count for record in records),
        "high_risk_events": sum(record.high_risk_event_count for record in records),
    }


def _group_events(events: list[AnnouncementEvent]) -> dict[str, list[AnnouncementEvent]]:
    grouped: dict[str, list[AnnouncementEvent]] = defaultdict(list)
    for event in events:
        grouped[event.ts_code].append(event)
    for rows in grouped.values():
        rows.sort(key=lambda event: event.event_time)
    return grouped


def _aggregate_reason(
    scored_events: list[EventScoreRecord],
    event_score: float,
    event_risk_score: float,
    block_buy_reasons: list[str],
) -> str:
    if block_buy_reasons:
        return "触发禁买：" + "；".join(block_buy_reasons)
    counts = Counter(
        "positive" if event.signed_event_score > 0 else "negative"
        for event in scored_events
        if event.signed_event_score != 0
    )
    neutral_count = sum(1 for event in scored_events if event.signed_event_score == 0)
    suffix = f"，中性事件 {neutral_count} 条" if neutral_count else ""
    return (
        f"正向事件 {counts['positive']} 条，负向事件 {counts['negative']} 条{suffix}，"
        f"事件分 {event_score:.1f}，风险分 {event_risk_score:.1f}"
    )
