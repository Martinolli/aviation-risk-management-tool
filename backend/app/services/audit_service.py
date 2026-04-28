import uuid
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction

WORKFLOW_AUDIT_ACTIONS = {
    AuditAction.SUBMIT,
    AuditAction.APPROVE,
    AuditAction.REJECT,
    AuditAction.ESCALATE,
    AuditAction.RETURN_FOR_REVISION,
}


def _to_json_compatible(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {
            str(_to_json_compatible(key)): _to_json_compatible(item)
            for key, item in value.items()
        }
    if isinstance(value, set):
        return [_to_json_compatible(item) for item in sorted(value, key=str)]
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_to_json_compatible(item) for item in value]
    return str(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _add_audit_log(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    field_name: str | None = None,
    old_value: Any = None,
    new_value: Any = None,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        field_name=field_name,
        old_value=_to_json_compatible(old_value),
        new_value=_to_json_compatible(new_value),
        changed_by_user_id=changed_by_user_id,
        changed_at=_utc_now(),
        reason=reason,
    )
    db.add(audit_log)
    db.flush()
    return audit_log


def log_change(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    field_name: str,
    old_value: Any,
    new_value: Any,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> AuditLog:
    return _add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.UPDATE,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        changed_by_user_id=changed_by_user_id,
        reason=reason,
    )


def log_entity_created(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    created_by_user_id: uuid.UUID | None = None,
    new_value: Any = None,
    reason: str | None = None,
) -> AuditLog:
    return _add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.CREATE,
        new_value=new_value,
        changed_by_user_id=created_by_user_id,
        reason=reason,
    )


def log_workflow_action(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    action: AuditAction,
    changed_by_user_id: uuid.UUID | None = None,
    old_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
) -> AuditLog:
    if action not in WORKFLOW_AUDIT_ACTIONS:
        raise ValueError(f"Unsupported workflow audit action: {action}")

    return _add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
        changed_by_user_id=changed_by_user_id,
        reason=reason,
    )


def log_archive_action(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None = None,
    old_value: Any = None,
    new_value: Any = None,
    reason: str | None = None,
) -> AuditLog:
    return _add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.ARCHIVE,
        old_value=old_value,
        new_value=new_value,
        changed_by_user_id=changed_by_user_id,
        reason=reason,
    )


def log_report_generated(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    generated_by_user_id: uuid.UUID | None = None,
    report_metadata: Any = None,
    reason: str | None = None,
) -> AuditLog:
    return _add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.GENERATE_REPORT,
        new_value=report_metadata,
        changed_by_user_id=generated_by_user_id,
        reason=reason,
    )


def log_llm_analysis(
    db: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None = None,
    llm_metadata: Any = None,
    reason: str | None = None,
) -> AuditLog:
    return _add_audit_log(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=AuditAction.LLM_ANALYSIS,
        new_value=llm_metadata,
        changed_by_user_id=changed_by_user_id,
        reason=reason,
    )
