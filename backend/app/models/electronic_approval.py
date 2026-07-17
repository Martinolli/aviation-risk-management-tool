from datetime import datetime
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    AuthorityLevel,
    ElectronicApprovalStatus,
    ElectronicApprovalTargetType,
)


class ElectronicApproval(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "electronic_approvals"

    target_type: Mapped[ElectronicApprovalTargetType] = mapped_column(
        Enum(ElectronicApprovalTargetType, native_enum=False),
        nullable=False,
        index=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    risk_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_records.id"), nullable=True, index=True
    )
    risk_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_decisions.id"), nullable=True, index=True
    )
    committee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("committees.id"), nullable=True
    )
    authority_level: Mapped[AuthorityLevel | None] = mapped_column(
        Enum(AuthorityLevel, native_enum=False)
    )
    approved_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    approval_statement: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledgement_text: Mapped[str] = mapped_column(Text, nullable=False)
    meaning_of_signature: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ElectronicApprovalStatus] = mapped_column(
        Enum(ElectronicApprovalStatus, native_enum=False),
        default=ElectronicApprovalStatus.APPROVED,
        nullable=False,
    )
    approval_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    approved_by_user = relationship("User")
    risk_record = relationship("RiskRecord")
    risk_decision = relationship("RiskDecision")
    committee = relationship("Committee")
