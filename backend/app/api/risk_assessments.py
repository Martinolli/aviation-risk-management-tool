import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.risk import RiskAssessment
from app.schemas.risk_assessment import (
    RiskAssessmentCreate,
    RiskAssessmentRead,
    RiskAssessmentUpdate,
)
from app.services.risk_assessment_service import (
    RiskAssessmentBusinessRuleError,
    RiskAssessmentNotFoundError,
    create_risk_assessment,
    get_risk_assessment,
    list_risk_assessments,
    update_risk_assessment,
)

router = APIRouter(prefix="/risk-assessments", tags=["risk-assessments"])


def _commit_and_refresh(
    db: Session,
    risk_assessment: RiskAssessment,
) -> RiskAssessment:
    db.commit()
    db.refresh(risk_assessment)
    return risk_assessment


@router.get("", response_model=list[RiskAssessmentRead])
def list_risk_assessments_endpoint(
    risk_record_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    return list_risk_assessments(db, risk_record_id=risk_record_id)


@router.get("/{risk_assessment_id}", response_model=RiskAssessmentRead)
def get_risk_assessment_endpoint(
    risk_assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    assessment = get_risk_assessment(db, risk_assessment_id=risk_assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk assessment not found",
        )
    return assessment


@router.post(
    "",
    response_model=RiskAssessmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_risk_assessment_endpoint(
    data: RiskAssessmentCreate,
    db: Session = Depends(get_db),
):
    try:
        assessment = create_risk_assessment(
            db,
            data=data,
            assessed_by_user_id=None,
        )
        return _commit_and_refresh(db, assessment)
    except RiskAssessmentBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/{risk_assessment_id}", response_model=RiskAssessmentRead)
def update_risk_assessment_endpoint(
    risk_assessment_id: uuid.UUID,
    data: RiskAssessmentUpdate,
    db: Session = Depends(get_db),
):
    try:
        assessment = update_risk_assessment(
            db,
            risk_assessment_id=risk_assessment_id,
            data=data,
            changed_by_user_id=None,
        )
        return _commit_and_refresh(db, assessment)
    except RiskAssessmentNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk assessment not found",
        ) from exc
    except RiskAssessmentBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
