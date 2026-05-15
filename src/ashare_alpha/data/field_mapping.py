from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FieldMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_to_internal: dict[str, str] = Field(default_factory=dict)
    required_internal_fields: tuple[str, ...] = Field(default_factory=tuple)

    def validate_required_fields(self, row: dict[str, object]) -> None:
        mapped = self.apply_mapping(row)
        missing = [
            field_name
            for field_name in self.required_internal_fields
            if field_name not in mapped or mapped[field_name] in {None, ""}
        ]
        if missing:
            raise ValueError(f"Missing required mapped fields: {', '.join(missing)}")

    def apply_mapping(self, row: dict[str, object]) -> dict[str, object]:
        mapped: dict[str, object] = {}
        for source_field, value in row.items():
            internal_field = self.source_to_internal.get(source_field, source_field)
            mapped[internal_field] = value
        return mapped


DAILY_BAR_REQUIRED_FIELDS = (
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "volume",
    "amount",
    "is_trading",
)
