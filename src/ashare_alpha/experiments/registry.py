from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ashare_alpha.experiments.models import ExperimentIndex, ExperimentRecord
from ashare_alpha.experiments.storage import (
    load_experiment_record,
    save_experiment_index,
    save_experiment_record,
)


class ExperimentRegistry:
    def __init__(self, registry_dir: Path = Path("outputs/experiments")) -> None:
        self.registry_dir = Path(registry_dir)
        self.records_dir = self.registry_dir / "records"
        self.index_path = self.registry_dir / "index.json"

    def add(self, record: ExperimentRecord, overwrite: bool = False) -> ExperimentRecord:
        record_path = self.records_dir / f"{record.experiment_id}.json"
        if record_path.exists() and not overwrite:
            raise ValueError(f"Experiment already exists: {record.experiment_id}")
        save_experiment_record(record, record_path)
        self.rebuild_index()
        return record

    def list(self) -> list[ExperimentRecord]:
        return sorted(self._load_records(), key=lambda item: item.created_at, reverse=True)

    def get(self, experiment_id: str) -> ExperimentRecord:
        path = self.records_dir / f"{experiment_id}.json"
        if not path.exists():
            raise ValueError(f"Experiment does not exist: {experiment_id}")
        return load_experiment_record(path)

    def find_by_tag(self, tag: str) -> list[ExperimentRecord]:
        return [record for record in self.list() if tag in record.tags]

    def find_by_command(self, command: str) -> list[ExperimentRecord]:
        return [record for record in self.list() if record.command == command]

    def rebuild_index(self) -> ExperimentIndex:
        index = ExperimentIndex(
            registry_dir=str(self.registry_dir),
            generated_at=datetime.now(),
            experiments=self.list(),
        )
        save_experiment_index(index, self.index_path)
        return index

    def _load_records(self) -> list[ExperimentRecord]:
        if not self.records_dir.exists():
            return []
        records: list[ExperimentRecord] = []
        for path in sorted(self.records_dir.glob("*.json")):
            try:
                records.append(load_experiment_record(path))
            except ValueError:
                continue
        return records
