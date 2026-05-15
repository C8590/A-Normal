from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FrontendModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class FrontendData(FrontendModel):
    generated_at: datetime
    outputs_root: str = Field(min_length=1)
    version: str = Field(min_length=1)
    summary: dict[str, Any] = Field(default_factory=dict)
    latest_pipeline: dict[str, Any] | None = None
    latest_backtest: dict[str, Any] | None = None
    latest_sweep: dict[str, Any] | None = None
    latest_walkforward: dict[str, Any] | None = None
    latest_candidate_selection: dict[str, Any] | None = None
    recent_experiments: list[dict[str, Any]] = Field(default_factory=list)
    top_candidates: list[dict[str, Any]] = Field(default_factory=list)
    warning_items: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
