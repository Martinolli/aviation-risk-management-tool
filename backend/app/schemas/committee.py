import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AuthorityLevel, CommitteeType


class CommitteeCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    authority_level: AuthorityLevel
    committee_type: CommitteeType

    model_config = ConfigDict(extra="forbid")


class CommitteeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeArchive(BaseModel):
    archive_reason: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class CommitteeRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    authority_level: AuthorityLevel
    committee_type: CommitteeType
    is_fixed: bool
    is_active: bool
    archived_at: datetime | None
    archive_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
