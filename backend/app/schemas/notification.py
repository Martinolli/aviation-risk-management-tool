from datetime import date, datetime
from enum import StrEnum
import uuid

from pydantic import BaseModel, ConfigDict


class NotificationSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


class NotificationCategory(StrEnum):
    ACTION = "ACTION"
    MONITORING = "MONITORING"
    DECISION_QUEUE = "DECISION_QUEUE"
    MEETING = "MEETING"


class NotificationRead(BaseModel):
    id: str
    category: NotificationCategory
    severity: NotificationSeverity
    title: str
    message: str
    target_type: str
    target_id: uuid.UUID
    risk_record_id: uuid.UUID | None = None
    risk_id: str | None = None
    committee_id: uuid.UUID | None = None
    committee_name: str | None = None
    due_date: date | None = None
    created_reference_at: datetime | None = None
    action_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class NotificationSummaryRead(BaseModel):
    total_count: int
    critical_count: int
    warning_count: int
    info_count: int
    action_count: int
    monitoring_count: int
    decision_queue_count: int
    meeting_count: int
    items: list[NotificationRead]
