import uuid

from pydantic import BaseModel, ConfigDict

from app.models.enums import AuthorityLevel, CommitteeType
from app.schemas.risk import RiskRecordRead


class MyDecisionQueueCommitteeRead(BaseModel):
    committee_id: uuid.UUID
    committee_name: str
    authority_level: AuthorityLevel
    committee_type: CommitteeType
    role_label: str | None = None
    queue_scope: str | list[str]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class MyDecisionQueueItemRead(BaseModel):
    risk_record: RiskRecordRead
    committee_id: uuid.UUID
    committee_name: str
    authority_level: AuthorityLevel
    role_label: str | None = None
    queue_reason: str

    model_config = ConfigDict(from_attributes=True)


class MyDecisionQueueRead(BaseModel):
    user_id: uuid.UUID
    committees: list[MyDecisionQueueCommitteeRead]
    queue_items: list[MyDecisionQueueItemRead]

    model_config = ConfigDict(from_attributes=True)
