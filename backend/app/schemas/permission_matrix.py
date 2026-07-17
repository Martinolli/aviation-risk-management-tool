from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionMatrixRuleRead(BaseModel):
    area: str
    capability: str
    allowed_roles_or_users: list[str]
    authority_level: str | None
    access_basis: str
    restrictions: str
    audit_expected: bool
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PermissionMatrixSectionRead(BaseModel):
    section: str
    description: str
    rules: list[PermissionMatrixRuleRead]

    model_config = ConfigDict(from_attributes=True)


class PermissionMatrixRead(BaseModel):
    policy_name: str
    policy_version: str
    effective_status: str
    generated_at: datetime
    summary: str
    principles: list[str]
    sections: list[PermissionMatrixSectionRead]

    model_config = ConfigDict(from_attributes=True)
