from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Text, Uuid, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LLMAnalysis(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "llm_analyses"

    risk_record_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk_records.id"), nullable=False
    )
    input_problem_description: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(100))
    output_json: Mapped[dict | list] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # LLMAnalysis is advisory only and does not represent approval or acceptance.
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    risk_record = relationship("RiskRecord")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    accepted_by_user = relationship("User", foreign_keys=[accepted_by_user_id])
