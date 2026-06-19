import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus


class RiskRecordCreate(BaseModel):
    problem_description: str = Field(..., min_length=1)
    source_trigger: str | None = None
    domain: RiskDomain = RiskDomain.OTHER
    board_of_origin_id: uuid.UUID | None = None
    system_scope: str | None = None
    central_event: str | None = None
    hazard_statement: str | None = None
    causes: list[str] | None = None
    consequences: list[str] | None = None
    existing_controls: list[str] | None = None
    owner_user_id: uuid.UUID | None = None

    model_config = ConfigDict(extra="forbid")


class RiskRecordUpdate(BaseModel):
    source_trigger: str | None = None
    domain: RiskDomain | None = None
    board_of_origin_id: uuid.UUID | None = None
    system_scope: str | None = None
    central_event: str | None = None
    hazard_statement: str | None = None
    causes: list[str] | None = None
    consequences: list[str] | None = None
    existing_controls: list[str] | None = None
    owner_user_id: uuid.UUID | None = None

    model_config = ConfigDict(extra="forbid")


class RiskRecordRead(BaseModel):
    id: uuid.UUID
    risk_id: str | None = None
    problem_description: str
    source_trigger: str | None
    domain: RiskDomain
    board_of_origin_id: uuid.UUID | None
    system_scope: str | None
    central_event: str | None
    hazard_statement: str | None
    causes: list[str] | None
    consequences: list[str] | None
    existing_controls: list[str] | None
    workflow_status: RiskWorkflowStatus
    lifecycle_status: RiskLifecycleStatus
    created_by_user_id: uuid.UUID | None
    owner_user_id: uuid.UUID | None
    is_active: bool
    archived_at: datetime | None
    archive_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskRecordSubmit(BaseModel):
    reason: str | None = None

    model_config = ConfigDict(extra="forbid")
