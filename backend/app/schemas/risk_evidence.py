import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RiskEvidenceRead(BaseModel):
    id: uuid.UUID
    risk_record_id: uuid.UUID
    original_filename: str
    content_type: str | None
    file_size_bytes: int
    description: str | None
    uploaded_by_user_id: uuid.UUID | None
    uploaded_at: datetime
    is_active: bool
    archived_at: datetime | None
    archived_by_user_id: uuid.UUID | None
    archive_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskEvidenceArchive(BaseModel):
    archive_reason: str | None = None

    model_config = ConfigDict(extra="forbid")


class RiskEvidenceUploadMetadata(BaseModel):
    description: str | None = None

    model_config = ConfigDict(extra="forbid")
