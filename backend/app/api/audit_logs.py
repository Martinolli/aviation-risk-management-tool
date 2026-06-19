import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.enums import AuditAction
from app.schemas.audit import AuditLogRead
from app.services.audit_query_service import (
    AuditQueryBusinessRuleError,
    get_audit_log,
    list_audit_logs,
)

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs_endpoint(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    try:
        return list_audit_logs(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changed_by_user_id=changed_by_user_id,
            limit=limit,
            offset=offset,
        )
    except AuditQueryBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{audit_log_id}", response_model=AuditLogRead)
def get_audit_log_endpoint(
    audit_log_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    audit_log = get_audit_log(db, audit_log_id=audit_log_id)
    if audit_log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    return audit_log
