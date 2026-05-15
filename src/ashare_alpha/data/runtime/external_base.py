from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ashare_alpha.data.runtime.context import SourceRuntimeContext
from ashare_alpha.data.runtime.models import MaterializationResult


class ExternalDataRuntimeAdapter(ABC):
    def __init__(self, context: SourceRuntimeContext, data_version: str, config_dir: Path) -> None:
        self.context = context
        self.data_version = data_version
        self.config_dir = Path(config_dir)

    def validate_runtime(self) -> list[str]:
        try:
            self.context.assert_can_run_offline()
        except RuntimeError as exc:
            return [str(exc)]
        return []

    @abstractmethod
    def materialize(self, output_dir: Path) -> MaterializationResult:
        """Materialize this source into the standard four-table local CSV layout."""
