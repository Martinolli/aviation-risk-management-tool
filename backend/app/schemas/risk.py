from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus


class RiskRecordCreate(BaseModel):
    problem_description: str = Field(..., min_length=1)
    source_trigger: str | None = None
    domain: RiskDomain = RiskDomain.OTHER
    system_scope: str | None = None
    central_event: str | None = None
    hazard_statement: str | None = None
    causes: list[str] | None = None
    consequences: list[str] | None = None
    existing_controls: list[str] | None = None


class RiskRecordRead(RiskRecordCreate):
    risk_id: str | None = None
    workflow_status: RiskWorkflowStatus
    lifecycle_status: RiskLifecycleStatus

    model_config = ConfigDict(from_attributes=True)
