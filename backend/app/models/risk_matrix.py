from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RiskSeverityLevel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_severity_levels"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    numeric_value: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    archived_by_user = relationship("User")


class RiskLikelihoodLevel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_likelihood_levels"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    numeric_value: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    archived_by_user = relationship("User")


class RiskLevel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_levels"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    numeric_value: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str | None] = mapped_column(String(50))
    is_tolerable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_mitigation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_escalation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    archived_by_user = relationship("User")


class RiskMatrixCell(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_matrix_cells"
    __table_args__ = (
        UniqueConstraint("severity_level_id", "likelihood_level_id"),
    )

    severity_level_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_severity_levels.id"), nullable=False
    )
    likelihood_level_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_likelihood_levels.id"), nullable=False
    )
    risk_level_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_levels.id"), nullable=False
    )
    score: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    severity_level = relationship("RiskSeverityLevel")
    likelihood_level = relationship("RiskLikelihoodLevel")
    risk_level = relationship("RiskLevel")
    archived_by_user = relationship("User")
