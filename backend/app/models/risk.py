from datetime import date, datetime
import uuid

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    RiskActionStatus,
    RiskAssessmentType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)


class RiskRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_records"

    risk_id: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    # Problem Description is the root field of the risk record.
    problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    source_trigger: Mapped[str | None] = mapped_column(String(255))
    domain: Mapped[RiskDomain] = mapped_column(
        Enum(RiskDomain, native_enum=False), nullable=False
    )
    board_of_origin_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("committees.id"), nullable=True
    )
    system_scope: Mapped[str | None] = mapped_column(Text)
    central_event: Mapped[str | None] = mapped_column(Text)
    hazard_statement: Mapped[str | None] = mapped_column(Text)
    causes: Mapped[list[str] | None] = mapped_column(JSON)
    consequences: Mapped[list[str] | None] = mapped_column(JSON)
    existing_controls: Mapped[list[str] | None] = mapped_column(JSON)
    workflow_status: Mapped[RiskWorkflowStatus] = mapped_column(
        Enum(RiskWorkflowStatus, native_enum=False),
        default=RiskWorkflowStatus.DRAFT,
        nullable=False,
    )
    lifecycle_status: Mapped[RiskLifecycleStatus] = mapped_column(
        Enum(RiskLifecycleStatus, native_enum=False),
        default=RiskLifecycleStatus.OPEN,
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    archive_reason: Mapped[str | None] = mapped_column(Text)

    board_of_origin = relationship("Committee")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    owner_user = relationship("User", foreign_keys=[owner_user_id])
    archived_by_user = relationship("User", foreign_keys=[archived_by_user_id])
    assessments: Mapped[list["RiskAssessment"]] = relationship(back_populates="risk_record")
    actions: Mapped[list["RiskAction"]] = relationship(back_populates="risk_record")
    decisions: Mapped[list["RiskDecision"]] = relationship(back_populates="risk_record")


class RiskAssessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_assessments"

    risk_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_records.id"), nullable=False
    )
    assessment_type: Mapped[RiskAssessmentType] = mapped_column(
        Enum(RiskAssessmentType, native_enum=False), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(100), nullable=False)
    likelihood: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(100), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
    assessed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    risk_record: Mapped[RiskRecord] = relationship(back_populates="assessments")
    assessed_by_user = relationship("User")


class RiskAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_actions"

    risk_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_records.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    action_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[RiskActionStatus] = mapped_column(
        Enum(RiskActionStatus, native_enum=False),
        default=RiskActionStatus.OPEN,
        nullable=False,
    )
    completion_notes: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    risk_record: Mapped[RiskRecord] = relationship(back_populates="actions")
    action_owner_user = relationship("User")


class RiskDecision(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_decisions"

    risk_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_records.id"), nullable=False
    )
    committee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("committees.id"), nullable=False
    )
    decision_type: Mapped[RiskDecisionType] = mapped_column(
        Enum(RiskDecisionType, native_enum=False), nullable=False
    )
    decision_text: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    risk_record: Mapped[RiskRecord] = relationship(back_populates="decisions")
    committee = relationship("Committee")
    decided_by_user = relationship("User")
