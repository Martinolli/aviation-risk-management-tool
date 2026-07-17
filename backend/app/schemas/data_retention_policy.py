from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DataRetentionPolicyItemRead(BaseModel):
    record_type: str
    description: str
    default_retention_period: str
    archive_rule: str
    deletion_rule: str
    owner: str
    notes: str

    model_config = ConfigDict(from_attributes=True)


class DataRetentionPolicyRead(BaseModel):
    policy_name: str
    policy_version: str
    effective_status: str
    generated_at: datetime
    summary: str
    principles: list[str]
    items: list[DataRetentionPolicyItemRead]
    no_hard_delete_record_types: list[str]
    requires_legal_or_investigation_hold_review: list[str]

    model_config = ConfigDict(from_attributes=True)
