import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AuthorityLevel,
    ElectronicApprovalStatus,
    ElectronicApprovalTargetType,
)


DEFAULT_ACKNOWLEDGEMENT_TEXT = (
    "I acknowledge that this electronic approval represents my reviewed and "
    "intentional approval within the Aviation Risk Management Tool. I understand "
    "this is a controlled approval record for SMS governance and audit "
    "traceability, not a cryptographic digital signature."
)

DEFAULT_MEANING_OF_SIGNATURE = (
    "This controlled approval record identifies the authenticated user, approval "
    "timestamp, approval target, Authority Level context, and acknowledgement "
    "text for SMS governance traceability."
)


class ElectronicApprovalCreate(BaseModel):
    target_type: ElectronicApprovalTargetType
    target_id: uuid.UUID
    approval_statement: str = Field(..., min_length=1)
    acknowledgement_text: str | None = None

    model_config = ConfigDict(extra="forbid")


class ElectronicApprovalRead(BaseModel):
    id: uuid.UUID
    target_type: ElectronicApprovalTargetType
    target_id: uuid.UUID
    risk_record_id: uuid.UUID | None
    risk_decision_id: uuid.UUID | None
    committee_id: uuid.UUID | None
    authority_level: AuthorityLevel | None
    approved_by_user_id: uuid.UUID
    approved_at: datetime
    approval_statement: str
    acknowledgement_text: str
    meaning_of_signature: str
    status: ElectronicApprovalStatus
    approval_hash: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ElectronicApprovalSummaryRead(BaseModel):
    id: uuid.UUID
    target_type: ElectronicApprovalTargetType
    target_id: uuid.UUID
    approved_by_user_id: uuid.UUID
    approved_at: datetime
    authority_level: AuthorityLevel | None
    status: ElectronicApprovalStatus
    approval_hash: str

    model_config = ConfigDict(from_attributes=True)
