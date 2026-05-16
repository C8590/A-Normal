from __future__ import annotations

import csv
from pathlib import Path

from ashare_alpha.factors.models import FactorDailyRecord


def save_factor_csv(records: list[FactorDailyRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(FactorDailyRecord.model_fields)
    with output_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = record.model_dump(mode="json")
            row["missing_reasons"] = ";".join(record.missing_reasons)
            row["adjusted_quality_flags"] = ";".join(record.adjusted_quality_flags)
            writer.writerow(row)
