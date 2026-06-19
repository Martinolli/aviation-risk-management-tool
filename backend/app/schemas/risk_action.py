import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskActionStatus


class RiskActionCreate(BaseModel):
    risk_record_id: uuid.UUID
    title: str = Field(..., min_length=1)
    description: str | None = None
    action_owner_user_id: uuid.UUID | None = None
    due_date: date | None = None

    model_config = ConfigDict(extra="forbid")


class RiskActionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    action_owner_user_id: uuid.UUID | None = None
    due_date: date | None = None
    status: RiskActionStatus | None = None
    completion_notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class RiskActionComplete(BaseModel):
    completion_notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class RiskActionRead(BaseModel):
    id: uuid.UUID
    risk_record_id: uuid.UUID
    title: str
    description: str | None
    action_owner_user_id: uuid.UUID | None
    due_date: date | None
    status: RiskActionStatus
    completion_notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
