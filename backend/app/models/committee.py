from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuthorityLevel, CommitteeType


class Committee(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "committees"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    authority_level: Mapped[AuthorityLevel] = mapped_column(
        Enum(AuthorityLevel, native_enum=False), nullable=False
    )
    committee_type: Mapped[CommitteeType] = mapped_column(
        Enum(CommitteeType, native_enum=False), nullable=False
    )
    # LOW level committees are configurable.
    # MIDDLE and HIGH committees are fixed and cannot be deleted.
    # Risk Management Committee and Executive Safety Management Committee are
    # protected governance entities.
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    archive_reason: Mapped[str | None] = mapped_column(Text)

    archived_by_user = relationship("User")
    members: Mapped[list["CommitteeMember"]] = relationship(back_populates="committee")


class CommitteeMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "committee_members"

    committee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("committees.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role_label: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    archive_reason: Mapped[str | None] = mapped_column(Text)

    committee: Mapped[Committee] = relationship(back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    archived_by_user = relationship("User", foreign_keys=[archived_by_user_id])
