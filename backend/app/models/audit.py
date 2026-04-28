from datetime import datetime
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuditAction


class AuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, native_enum=False), nullable=False
    )
    field_name: Mapped[str | None] = mapped_column(String(255))
    old_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    new_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    changed_by_user = relationship("User")
