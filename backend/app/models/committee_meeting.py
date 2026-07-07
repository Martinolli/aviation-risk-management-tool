from datetime import date, datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    CommitteeMeetingAttendanceStatus,
    CommitteeMeetingStatus,
)


class CommitteeMeeting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "committee_meetings"

    committee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("committees.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    meeting_time_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    location: Mapped[str | None] = mapped_column(String(255))
    chair_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[CommitteeMeetingStatus] = mapped_column(
        Enum(CommitteeMeetingStatus, native_enum=False),
        default=CommitteeMeetingStatus.DRAFT,
        nullable=False,
        index=True,
    )
    agenda_summary: Mapped[str | None] = mapped_column(Text)
    discussion_summary: Mapped[str | None] = mapped_column(Text)
    decisions_summary: Mapped[str | None] = mapped_column(Text)
    action_items_summary: Mapped[str | None] = mapped_column(Text)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finalized_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    committee = relationship("Committee")
    chair_user = relationship("User", foreign_keys=[chair_user_id])
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    finalized_by_user = relationship("User", foreign_keys=[finalized_by_user_id])
    attendees: Mapped[list["CommitteeMeetingAttendee"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="CommitteeMeetingAttendee.created_at",
    )
    risk_items: Mapped[list["CommitteeMeetingRiskItem"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        order_by="CommitteeMeetingRiskItem.agenda_item_number",
    )

    @property
    def committee_name(self) -> str | None:
        return self.committee.name if self.committee is not None else None

    @property
    def authority_level(self) -> str | None:
        return (
            self.committee.authority_level.value
            if self.committee is not None and self.committee.authority_level is not None
            else None
        )

    @property
    def committee_type(self) -> str | None:
        return (
            self.committee.committee_type.value
            if self.committee is not None and self.committee.committee_type is not None
            else None
        )


class CommitteeMeetingAttendee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "committee_meeting_attendees"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("committee_meetings.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    attendee_name: Mapped[str | None] = mapped_column(String(255))
    attendee_email: Mapped[str | None] = mapped_column(String(320))
    role_label: Mapped[str | None] = mapped_column(String(100))
    attendance_status: Mapped[CommitteeMeetingAttendanceStatus] = mapped_column(
        Enum(CommitteeMeetingAttendanceStatus, native_enum=False),
        default=CommitteeMeetingAttendanceStatus.PRESENT,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    meeting: Mapped[CommitteeMeeting] = relationship(back_populates="attendees")
    user = relationship("User")


class CommitteeMeetingRiskItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "committee_meeting_risk_items"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("committee_meetings.id"),
        nullable=False,
        index=True,
    )
    risk_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_records.id"), nullable=False, index=True
    )
    agenda_item_number: Mapped[int | None] = mapped_column(Integer)
    discussion_summary: Mapped[str | None] = mapped_column(Text)
    decision_summary: Mapped[str | None] = mapped_column(Text)
    action_items: Mapped[str | None] = mapped_column(Text)
    linked_risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_decisions.id"), nullable=True
    )
    follow_up_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    follow_up_notes: Mapped[str | None] = mapped_column(Text)

    meeting: Mapped[CommitteeMeeting] = relationship(back_populates="risk_items")
    risk_record = relationship("RiskRecord")
    linked_risk_decision = relationship("RiskDecision")

    @property
    def risk_id(self) -> str | None:
        return self.risk_record.risk_id if self.risk_record is not None else None

    @property
    def risk_problem_description(self) -> str | None:
        return (
            self.risk_record.problem_description
            if self.risk_record is not None
            else None
        )

    @property
    def risk_domain(self) -> str | None:
        return (
            self.risk_record.domain.value
            if self.risk_record is not None and self.risk_record.domain is not None
            else None
        )

    @property
    def risk_workflow_status(self) -> str | None:
        return (
            self.risk_record.workflow_status.value
            if self.risk_record is not None
            and self.risk_record.workflow_status is not None
            else None
        )
