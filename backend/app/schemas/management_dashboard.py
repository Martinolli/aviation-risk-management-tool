from datetime import date, datetime
import uuid

from pydantic import BaseModel, ConfigDict


class ManagementDashboardKpi(BaseModel):
    key: str
    label: str
    value: int
    detail: str | None = None
    severity: str | None = None


class ManagementDashboardRiskSummary(BaseModel):
    risk_record_id: uuid.UUID
    risk_id: str | None
    problem_description: str
    domain: str
    workflow_status: str
    lifecycle_status: str
    latest_risk_level: str | None
    board_of_origin_id: uuid.UUID | None
    board_of_origin_name: str | None
    owner_user_id: uuid.UUID | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ManagementDashboardGroup(BaseModel):
    key: str
    label: str
    count: int


class ManagementDashboardAttentionItem(BaseModel):
    category: str
    severity: str
    title: str
    message: str
    target_type: str
    target_id: uuid.UUID
    risk_record_id: uuid.UUID | None = None
    risk_id: str | None = None
    action_url: str | None = None
    due_date: date | None = None


class ManagementDashboardRead(BaseModel):
    generated_at: datetime
    kpis: list[ManagementDashboardKpi]
    risk_level_distribution: list[ManagementDashboardGroup]
    domain_hotspots: list[ManagementDashboardGroup]
    workflow_backlog: list[ManagementDashboardGroup]
    authority_level_backlog: list[ManagementDashboardGroup]
    top_attention_items: list[ManagementDashboardAttentionItem]
    high_exposure_risks: list[ManagementDashboardRiskSummary]
    overdue_action_risks: list[ManagementDashboardRiskSummary]
    monitoring_concern_risks: list[ManagementDashboardRiskSummary]
    committee_backlog_risks: list[ManagementDashboardRiskSummary]
