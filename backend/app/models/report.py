from datetime import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GeneratedReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "generated_reports"

    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_record_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_records.id"), nullable=True
    )
    committee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("committees.id"), nullable=True
    )
    generated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_hash: Mapped[str | None] = mapped_column(String(128))
    template_version: Mapped[str] = mapped_column(String(50), nullable=False)

    risk_record = relationship("RiskRecord")
    committee = relationship("Committee")
    generated_by_user = relationship("User")
