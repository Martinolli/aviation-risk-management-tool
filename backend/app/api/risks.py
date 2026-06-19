import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.risk import RiskRecord
from app.schemas.risk import (
    RiskRecordCreate,
    RiskRecordRead,
    RiskRecordSubmit,
    RiskRecordUpdate,
)
from app.schemas.risk_detail import RiskRecordDetailRead
from app.services.risk_detail_service import (
    RiskDetailNotFoundError,
    get_risk_record_detail,
)
from app.services.risk_service import (
    RiskRecordBusinessRuleError,
    RiskRecordNotFoundError,
    create_risk_record,
    get_risk_record,
    list_risk_records,
    submit_risk_record,
    update_risk_record,
)

router = APIRouter(prefix="/risks", tags=["risks"])


def _commit_and_refresh(db: Session, risk_record: RiskRecord) -> RiskRecord:
    db.commit()
    db.refresh(risk_record)
    return risk_record


@router.get("", response_model=list[RiskRecordRead])
def list_risk_records_endpoint(
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    return list_risk_records(db, include_archived=include_archived)


@router.get("/{risk_record_id}/detail", response_model=RiskRecordDetailRead)
def get_risk_record_detail_endpoint(
    risk_record_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    try:
        return get_risk_record_detail(db, risk_record_id=risk_record_id)
    except RiskDetailNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk record not found",
        ) from exc


@router.get("/{risk_record_id}", response_model=RiskRecordRead)
def get_risk_record_endpoint(
    risk_record_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    risk_record = get_risk_record(db, risk_record_id=risk_record_id)
    if risk_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk record not found",
        )
    return risk_record


@router.post("", response_model=RiskRecordRead, status_code=status.HTTP_201_CREATED)
def create_risk_record_endpoint(
    data: RiskRecordCreate,
    db: Session = Depends(get_db),
):
    try:
        risk_record = create_risk_record(
            db,
            data=data,
            created_by_user_id=None,
        )
        return _commit_and_refresh(db, risk_record)
    except RiskRecordBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/{risk_record_id}", response_model=RiskRecordRead)
def update_risk_record_endpoint(
    risk_record_id: uuid.UUID,
    data: RiskRecordUpdate,
    db: Session = Depends(get_db),
):
    try:
        risk_record = update_risk_record(
            db,
            risk_record_id=risk_record_id,
            data=data,
            changed_by_user_id=None,
        )
        return _commit_and_refresh(db, risk_record)
    except RiskRecordNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk record not found",
        ) from exc
    except RiskRecordBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{risk_record_id}/submit", response_model=RiskRecordRead)
def submit_risk_record_endpoint(
    risk_record_id: uuid.UUID,
    data: RiskRecordSubmit | None = None,
    db: Session = Depends(get_db),
):
    try:
        risk_record = submit_risk_record(
            db,
            risk_record_id=risk_record_id,
            changed_by_user_id=None,
            reason=data.reason if data is not None else None,
        )
        return _commit_and_refresh(db, risk_record)
    except RiskRecordNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk record not found",
        ) from exc
    except RiskRecordBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
