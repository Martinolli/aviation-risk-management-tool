import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction

MAX_AUDIT_LOG_LIMIT = 500


class AuditQueryBusinessRuleError(ValueError):
    pass


def get_audit_log(
    db: Session,
    *,
    audit_log_id: uuid.UUID,
) -> AuditLog | None:
    return db.get(AuditLog, audit_log_id)


def list_audit_logs(
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    if limit < 1:
        raise AuditQueryBusinessRuleError("limit must be at least 1")
    if offset < 0:
        raise AuditQueryBusinessRuleError("offset must be at least 0")

    effective_limit = min(limit, MAX_AUDIT_LOG_LIMIT)
    statement = select(AuditLog).order_by(AuditLog.changed_at.desc())

    if entity_type is not None:
        statement = statement.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(AuditLog.entity_id == entity_id)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if changed_by_user_id is not None:
        statement = statement.where(AuditLog.changed_by_user_id == changed_by_user_id)

    statement = statement.limit(effective_limit).offset(offset)
    return list(db.scalars(statement).all())
