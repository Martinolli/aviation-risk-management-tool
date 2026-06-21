import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskAssessmentType


class RiskAssessmentCreate(BaseModel):
    risk_record_id: uuid.UUID
    assessment_type: RiskAssessmentType
    severity: str | None = Field(default=None, min_length=1)
    likelihood: str | None = Field(default=None, min_length=1)
    risk_level: str | None = Field(default=None, min_length=1)
    rationale: str | None = None
    severity_level_id: uuid.UUID | None = None
    likelihood_level_id: uuid.UUID | None = None

    model_config = ConfigDict(extra="forbid")


class RiskAssessmentUpdate(BaseModel):
    severity: str | None = Field(default=None, min_length=1)
    likelihood: str | None = Field(default=None, min_length=1)
    risk_level: str | None = Field(default=None, min_length=1)
    rationale: str | None = None
    severity_level_id: uuid.UUID | None = None
    likelihood_level_id: uuid.UUID | None = None
    clear_matrix_calculation: bool = False

    model_config = ConfigDict(extra="forbid")


class RiskAssessmentRead(BaseModel):
    id: uuid.UUID
    risk_record_id: uuid.UUID
    assessment_type: RiskAssessmentType
    severity: str
    likelihood: str
    risk_level: str
    rationale: str | None
    assessed_by_user_id: uuid.UUID | None
    assessed_at: datetime
    severity_level_id: uuid.UUID | None
    likelihood_level_id: uuid.UUID | None
    calculated_risk_level_id: uuid.UUID | None
    matrix_cell_id: uuid.UUID | None
    calculated_score: int | None
    is_tolerable: bool | None
    requires_mitigation: bool | None
    requires_escalation: bool | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
