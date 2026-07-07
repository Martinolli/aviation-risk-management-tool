import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    CommitteeMeetingAttendanceStatus,
    CommitteeMeetingStatus,
)


class CommitteeMeetingAttendeeCreate(BaseModel):
    user_id: uuid.UUID | None = None
    attendee_name: str | None = None
    attendee_email: str | None = None
    role_label: str | None = None
    attendance_status: CommitteeMeetingAttendanceStatus = (
        CommitteeMeetingAttendanceStatus.PRESENT
    )
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_attendee_identity(self):
        if self.user_id is None and not (self.attendee_name or "").strip():
            raise ValueError("Either user_id or attendee_name must be provided")
        return self


class CommitteeMeetingAttendeeUpdate(BaseModel):
    user_id: uuid.UUID | None = None
    attendee_name: str | None = None
    attendee_email: str | None = None
    role_label: str | None = None
    attendance_status: CommitteeMeetingAttendanceStatus | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMeetingAttendeeRead(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    user_id: uuid.UUID | None
    attendee_name: str | None
    attendee_email: str | None
    role_label: str | None
    attendance_status: CommitteeMeetingAttendanceStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommitteeMeetingRiskItemCreate(BaseModel):
    risk_record_id: uuid.UUID
    agenda_item_number: int | None = None
    discussion_summary: str | None = None
    decision_summary: str | None = None
    action_items: str | None = None
    linked_risk_decision_id: uuid.UUID | None = None
    follow_up_required: bool = False
    follow_up_notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMeetingRiskItemUpdate(BaseModel):
    agenda_item_number: int | None = None
    discussion_summary: str | None = None
    decision_summary: str | None = None
    action_items: str | None = None
    linked_risk_decision_id: uuid.UUID | None = None
    follow_up_required: bool | None = None
    follow_up_notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMeetingRiskItemRead(BaseModel):
    id: uuid.UUID
    meeting_id: uuid.UUID
    risk_record_id: uuid.UUID
    agenda_item_number: int | None
    discussion_summary: str | None
    decision_summary: str | None
    action_items: str | None
    linked_risk_decision_id: uuid.UUID | None
    follow_up_required: bool
    follow_up_notes: str | None
    risk_id: str | None
    risk_problem_description: str | None
    risk_domain: str | None
    risk_workflow_status: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommitteeMeetingCreate(BaseModel):
    committee_id: uuid.UUID
    title: str = Field(..., min_length=1)
    meeting_date: date
    meeting_time_utc: datetime | None = None
    location: str | None = None
    chair_user_id: uuid.UUID | None = None
    agenda_summary: str | None = None
    discussion_summary: str | None = None
    decisions_summary: str | None = None
    action_items_summary: str | None = None
    attendees: list[CommitteeMeetingAttendeeCreate] = Field(default_factory=list)
    risk_items: list[CommitteeMeetingRiskItemCreate] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class CommitteeMeetingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    meeting_date: date | None = None
    meeting_time_utc: datetime | None = None
    location: str | None = None
    chair_user_id: uuid.UUID | None = None
    agenda_summary: str | None = None
    discussion_summary: str | None = None
    decisions_summary: str | None = None
    action_items_summary: str | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMeetingFinalize(BaseModel):
    finalization_notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMeetingCancel(BaseModel):
    cancellation_reason: str | None = None

    model_config = ConfigDict(extra="forbid")


class CommitteeMeetingRead(BaseModel):
    id: uuid.UUID
    committee_id: uuid.UUID
    title: str
    meeting_date: date
    meeting_time_utc: datetime | None
    location: str | None
    chair_user_id: uuid.UUID | None
    created_by_user_id: uuid.UUID | None
    status: CommitteeMeetingStatus
    agenda_summary: str | None
    discussion_summary: str | None
    decisions_summary: str | None
    action_items_summary: str | None
    finalized_at: datetime | None
    finalized_by_user_id: uuid.UUID | None
    cancellation_reason: str | None
    is_active: bool
    committee_name: str | None
    authority_level: str | None
    committee_type: str | None
    attendees: list[CommitteeMeetingAttendeeRead]
    risk_items: list[CommitteeMeetingRiskItemRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
