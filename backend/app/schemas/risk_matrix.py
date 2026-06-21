import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class _ReferenceCreate(BaseModel):
    code: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str | None = None
    numeric_value: int = Field(..., gt=0)

    model_config = ConfigDict(extra="forbid")


class _ReferenceUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1)
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    numeric_value: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class _ReferenceRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    numeric_value: int
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskSeverityLevelCreate(_ReferenceCreate):
    pass


class RiskSeverityLevelUpdate(_ReferenceUpdate):
    pass


class RiskSeverityLevelRead(_ReferenceRead):
    pass


class RiskLikelihoodLevelCreate(_ReferenceCreate):
    pass


class RiskLikelihoodLevelUpdate(_ReferenceUpdate):
    pass


class RiskLikelihoodLevelRead(_ReferenceRead):
    pass


class RiskLevelCreate(_ReferenceCreate):
    color: str | None = None
    is_tolerable: bool = False
    requires_mitigation: bool = True
    requires_escalation: bool = False


class RiskLevelUpdate(_ReferenceUpdate):
    color: str | None = None
    is_tolerable: bool | None = None
    requires_mitigation: bool | None = None
    requires_escalation: bool | None = None


class RiskLevelRead(_ReferenceRead):
    color: str | None
    is_tolerable: bool
    requires_mitigation: bool
    requires_escalation: bool


class RiskMatrixCellCreate(BaseModel):
    severity_level_id: uuid.UUID
    likelihood_level_id: uuid.UUID
    risk_level_id: uuid.UUID
    score: int | None = Field(default=None, gt=0)
    label: str | None = None

    model_config = ConfigDict(extra="forbid")


class RiskMatrixCellUpdate(BaseModel):
    risk_level_id: uuid.UUID | None = None
    score: int | None = Field(default=None, gt=0)
    label: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class RiskMatrixCellRead(BaseModel):
    id: uuid.UUID
    severity_level_id: uuid.UUID
    likelihood_level_id: uuid.UUID
    risk_level_id: uuid.UUID
    score: int | None
    label: str | None
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RiskMatrixArchive(BaseModel):
    reason: str | None = None

    model_config = ConfigDict(extra="forbid")
