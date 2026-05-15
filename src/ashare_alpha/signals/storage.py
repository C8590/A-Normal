from __future__ import annotations

import csv
from pathlib import Path

from ashare_alpha.signals.models import SignalDailyRecord


def save_signal_csv(records: list[SignalDailyRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(SignalDailyRecord.model_fields)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            row["universe_exclude_reasons"] = ";".join(record.universe_exclude_reasons)
            row["buy_reasons"] = "；".join(record.buy_reasons)
            row["risk_reasons"] = "；".join(record.risk_reasons)
            writer.writerow(row)
