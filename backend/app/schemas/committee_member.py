import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommitteeMemberCreate(BaseModel):
    committee_id: uuid.UUID
    user_id: uuid.UUID
    role_label: str | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMemberUpdate(BaseModel):
    role_label: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMemberRead(BaseModel):
    id: uuid.UUID
    committee_id: uuid.UUID
    user_id: uuid.UUID
    role_label: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
