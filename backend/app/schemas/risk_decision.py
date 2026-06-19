import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskDecisionType


class RiskDecisionCreate(BaseModel):
    risk_record_id: uuid.UUID
    committee_id: uuid.UUID
    decision_type: RiskDecisionType
    decision_text: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class RiskDecisionRead(BaseModel):
    id: uuid.UUID
    risk_record_id: uuid.UUID
    committee_id: uuid.UUID
    decision_type: RiskDecisionType
    decision_text: str
    decided_by_user_id: uuid.UUID | None
    decided_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
