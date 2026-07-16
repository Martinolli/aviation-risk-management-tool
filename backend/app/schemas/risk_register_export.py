import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class RiskRegisterExportFormat(StrEnum):
    CSV = "CSV"
    DOCX = "DOCX"


class RiskRegisterExportMetadata(BaseModel):
    generated_at: datetime
    generated_by_user_id: uuid.UUID | None
    record_count: int
    filters: dict[str, Any]
