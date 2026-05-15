from __future__ import annotations

import csv
from pathlib import Path

from ashare_alpha.events.models import EventDailyRecord


def save_event_daily_csv(records: list[EventDailyRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(EventDailyRecord.model_fields)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            row["block_buy_reasons"] = "；".join(record.block_buy_reasons)
            writer.writerow(row)
