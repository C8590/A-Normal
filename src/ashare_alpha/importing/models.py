from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ImportStatus = Literal["SUCCESS", "FAILED"]


class ImportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImportedFile(ImportModel):
    dataset_name: str = Field(min_length=1)
    source_path: str
    target_path: str
    rows: int | None = None
    sha256: str = Field(min_length=1)
    copied: bool


class ImportManifest(ImportModel):
    import_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    data_version: str = Field(min_length=1)
    created_at: datetime
    source_data_dir: str
    target_data_dir: str
    config_dir: str | None = None
    copied_files: list[ImportedFile] = Field(default_factory=list)
    row_counts: dict[str, int] = Field(default_factory=dict)
    validation_passed: bool
    validation_error_count: int = Field(ge=0)
    validation_warning_count: int = Field(ge=0)
    snapshot_id: str | None = None
    snapshot_path: str | None = None
    status: ImportStatus
    error_message: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_status(self) -> ImportManifest:
        if self.status == "FAILED" and not self.error_message:
            raise ValueError("error_message must not be empty when status is FAILED")
        if self.status == "SUCCESS" and not self.copied_files:
            raise ValueError("copied_files must not be empty when status is SUCCESS")
        return self
