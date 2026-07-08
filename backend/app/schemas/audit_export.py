import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.enums import AuditAction


class AuditExportFormat(StrEnum):
    CSV = "CSV"
    DOCX = "DOCX"


class AuditLogExportFilters(BaseModel):
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    action: AuditAction | None = None
    changed_by_user_id: uuid.UUID | None = None
    changed_at_from: datetime | None = None
    changed_at_to: datetime | None = None
    limit: int = 500
    offset: int = 0

    model_config = ConfigDict(extra="forbid")

    @field_validator("entity_type", mode="before")
    @classmethod
    def _trim_blank_entity_type(cls, value: Any) -> Any:
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value

    @field_validator("limit")
    @classmethod
    def _validate_limit(cls, value: int) -> int:
        if value < 1:
            raise ValueError("limit must be at least 1")
        if value > 5000:
            raise ValueError("limit must be at most 5000")
        return value

    @field_validator("offset")
    @classmethod
    def _validate_offset(cls, value: int) -> int:
        if value < 0:
            raise ValueError("offset must be at least 0")
        return value

    @model_validator(mode="after")
    def _validate_date_range(self) -> "AuditLogExportFilters":
        if (
            self.changed_at_from is not None
            and self.changed_at_to is not None
            and self.changed_at_from > self.changed_at_to
        ):
            raise ValueError("changed_at_from must not be after changed_at_to")
        return self
