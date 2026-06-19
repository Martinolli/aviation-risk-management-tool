from datetime import datetime

from pydantic import BaseModel

from app.schemas.risk import RiskRecordRead
from app.schemas.risk_action import RiskActionRead
from app.schemas.risk_assessment import RiskAssessmentRead
from app.schemas.risk_decision import RiskDecisionRead


class RiskAuditSummary(BaseModel):
    total_count: int
    create_count: int
    update_count: int
    workflow_count: int
    latest_changed_at: datetime | None


class RiskRecordDetailRead(BaseModel):
    risk_record: RiskRecordRead
    assessments: list[RiskAssessmentRead]
    actions: list[RiskActionRead]
    decisions: list[RiskDecisionRead]
    audit_summary: RiskAuditSummary
