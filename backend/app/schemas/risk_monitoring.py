import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskMonitoringReviewOutcome, RiskMonitoringStatus


class RiskMonitoringReviewCreate(BaseModel):
    risk_record_id: uuid.UUID
    monitoring_owner_user_id: uuid.UUID | None = None
    review_frequency: str | None = Field(default=None, max_length=100)
    next_review_date: date | None = None
    review_notes: str | None = None
    effectiveness_review: str | None = None

    model_config = ConfigDict(extra="forbid")


class RiskMonitoringReviewUpdate(BaseModel):
    monitoring_owner_user_id: uuid.UUID | None = None
    review_frequency: str | None = Field(default=None, max_length=100)
    next_review_date: date | None = None
    status: RiskMonitoringStatus | None = None
    review_notes: str | None = None
    effectiveness_review: str | None = None
    review_outcome: RiskMonitoringReviewOutcome | None = None

    model_config = ConfigDict(extra="forbid")


class RiskMonitoringReviewComplete(BaseModel):
    effectiveness_review: str = Field(min_length=1)
    review_outcome: RiskMonitoringReviewOutcome
    next_review_date: date | None = None
    review_notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class RiskMonitoringReviewClose(BaseModel):
    closure_reason: str | None = None

    model_config = ConfigDict(extra="forbid")


class RiskMonitoringReviewRead(BaseModel):
    id: uuid.UUID
    risk_record_id: uuid.UUID
    monitoring_owner_user_id: uuid.UUID | None
    review_frequency: str | None
    next_review_date: date | None
    last_reviewed_at: datetime | None
    status: RiskMonitoringStatus
    review_notes: str | None
    effectiveness_review: str | None
    review_outcome: RiskMonitoringReviewOutcome | None
    reviewed_by_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    closed_at: datetime | None
    closed_by_user_id: uuid.UUID | None
    closure_reason: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
