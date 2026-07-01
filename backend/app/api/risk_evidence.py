import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.risk import RiskEvidence
from app.models.user import User
from app.schemas.risk_evidence import RiskEvidenceArchive, RiskEvidenceRead
from app.services.risk_evidence_service import (
    RiskEvidenceBusinessRuleError,
    RiskEvidenceNotFoundError,
    archive_risk_evidence,
    get_risk_evidence,
    get_risk_evidence_file_path,
    list_risk_evidence,
    upload_risk_evidence,
)

router = APIRouter(prefix="/risk-evidence", tags=["risk-evidence"])


def _commit_and_refresh(db: Session, evidence: RiskEvidence) -> RiskEvidence:
    db.commit()
    db.refresh(evidence)
    return evidence


def _not_found(exc: RiskEvidenceNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _business_rule(exc: RiskEvidenceBusinessRuleError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/{risk_record_id}/upload",
    response_model=RiskEvidenceRead,
    status_code=status.HTTP_201_CREATED,
)
def upload_risk_evidence_endpoint(
    risk_record_id: uuid.UUID,
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        evidence = upload_risk_evidence(
            db,
            risk_record_id=risk_record_id,
            upload_file=file,
            description=description,
            uploaded_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, evidence)
    except RiskEvidenceNotFoundError as exc:
        db.rollback()
        raise _not_found(exc) from exc
    except RiskEvidenceBusinessRuleError as exc:
        db.rollback()
        raise _business_rule(exc) from exc


@router.get("/risk/{risk_record_id}", response_model=list[RiskEvidenceRead])
def list_risk_evidence_endpoint(
    risk_record_id: uuid.UUID,
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return list_risk_evidence(
            db,
            risk_record_id=risk_record_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
            include_archived=include_archived,
        )
    except RiskEvidenceNotFoundError as exc:
        raise _not_found(exc) from exc
    except RiskEvidenceBusinessRuleError as exc:
        raise _business_rule(exc) from exc


@router.get("/{evidence_id}/download")
def download_risk_evidence_endpoint(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        evidence, file_path = get_risk_evidence_file_path(
            db,
            evidence_id=evidence_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
        )
    except RiskEvidenceNotFoundError as exc:
        raise _not_found(exc) from exc
    except RiskEvidenceBusinessRuleError as exc:
        raise _business_rule(exc) from exc

    return FileResponse(
        path=file_path,
        media_type=evidence.content_type or "application/octet-stream",
        filename=evidence.original_filename,
    )


@router.post("/{evidence_id}/archive", response_model=RiskEvidenceRead)
def archive_risk_evidence_endpoint(
    evidence_id: uuid.UUID,
    data: RiskEvidenceArchive,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        evidence = archive_risk_evidence(
            db,
            evidence_id=evidence_id,
            archived_by_user_id=get_optional_current_user_id(current_user),
            archive_reason=data.archive_reason,
        )
        return _commit_and_refresh(db, evidence)
    except RiskEvidenceNotFoundError as exc:
        db.rollback()
        raise _not_found(exc) from exc
    except RiskEvidenceBusinessRuleError as exc:
        db.rollback()
        raise _business_rule(exc) from exc


@router.get("/{evidence_id}", response_model=RiskEvidenceRead)
def get_risk_evidence_endpoint(
    evidence_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return get_risk_evidence(
            db,
            evidence_id=evidence_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
        )
    except RiskEvidenceNotFoundError as exc:
        raise _not_found(exc) from exc
    except RiskEvidenceBusinessRuleError as exc:
        raise _business_rule(exc) from exc
