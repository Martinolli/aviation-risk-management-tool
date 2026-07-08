import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.enums import AuditAction
from app.models.user import User
from app.schemas.audit import AuditLogRead
from app.schemas.audit_export import AuditLogExportFilters
from app.services.audit_export_service import (
    AuditExportBusinessRuleError,
    export_audit_logs_csv,
    export_audit_logs_docx,
)
from app.services.audit_query_service import (
    AuditQueryBusinessRuleError,
    get_audit_log,
    list_audit_logs,
)

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])
AUDIT_EXPORT_OUTPUT_DIR = Path("generated_reports")


def _build_export_filters(
    *,
    entity_type: str | None,
    entity_id: uuid.UUID | None,
    action: AuditAction | None,
    changed_by_user_id: uuid.UUID | None,
    changed_at_from: datetime | None,
    changed_at_to: datetime | None,
    limit: int,
    offset: int,
) -> AuditLogExportFilters:
    try:
        return AuditLogExportFilters(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changed_by_user_id=changed_by_user_id,
            changed_at_from=changed_at_from,
            changed_at_to=changed_at_to,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        first_error = exc.errors()[0] if exc.errors() else {}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(first_error.get("msg", "Invalid audit export filters.")),
        ) from exc


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs_endpoint(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    changed_at_from: datetime | None = None,
    changed_at_to: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return list_audit_logs(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            changed_by_user_id=changed_by_user_id,
            changed_at_from=changed_at_from,
            changed_at_to=changed_at_to,
            limit=limit,
            offset=offset,
        )
    except AuditQueryBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/export/csv")
def export_audit_logs_csv_endpoint(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    changed_at_from: datetime | None = None,
    changed_at_to: datetime | None = None,
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    filters = _build_export_filters(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by_user_id=changed_by_user_id,
        changed_at_from=changed_at_from,
        changed_at_to=changed_at_to,
        limit=limit,
        offset=offset,
    )
    try:
        file_path = export_audit_logs_csv(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            filters=filters,
            output_dir=AUDIT_EXPORT_OUTPUT_DIR,
        )
    except AuditExportBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=file_path.name,
    )


@router.get("/export/docx")
def export_audit_logs_docx_endpoint(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: AuditAction | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    changed_at_from: datetime | None = None,
    changed_at_to: datetime | None = None,
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    filters = _build_export_filters(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by_user_id=changed_by_user_id,
        changed_at_from=changed_at_from,
        changed_at_to=changed_at_to,
        limit=limit,
        offset=offset,
    )
    try:
        file_path = export_audit_logs_docx(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            filters=filters,
            output_dir=AUDIT_EXPORT_OUTPUT_DIR,
        )
    except AuditExportBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return FileResponse(
        path=file_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
        filename=file_path.name,
    )


@router.get("/{audit_log_id}", response_model=AuditLogRead)
def get_audit_log_endpoint(
    audit_log_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        audit_log = get_audit_log(
            db,
            audit_log_id=audit_log_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
        )
        if audit_log is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audit log not found",
            )
        return audit_log
    except AuditQueryBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
