import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.risk import RiskDecision
from app.schemas.risk_decision import RiskDecisionCreate, RiskDecisionRead
from app.services.risk_decision_service import (
    RiskDecisionBusinessRuleError,
    create_risk_decision,
    get_risk_decision,
    list_risk_decisions,
)

router = APIRouter(prefix="/risk-decisions", tags=["risk-decisions"])


def _commit_and_refresh(db: Session, risk_decision: RiskDecision) -> RiskDecision:
    db.commit()
    db.refresh(risk_decision)
    return risk_decision


@router.get("", response_model=list[RiskDecisionRead])
def list_risk_decisions_endpoint(
    risk_record_id: uuid.UUID | None = None,
    committee_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    return list_risk_decisions(
        db,
        risk_record_id=risk_record_id,
        committee_id=committee_id,
    )


@router.get("/{risk_decision_id}", response_model=RiskDecisionRead)
def get_risk_decision_endpoint(
    risk_decision_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    decision = get_risk_decision(db, risk_decision_id=risk_decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk decision not found",
        )
    return decision


@router.post("", response_model=RiskDecisionRead, status_code=status.HTTP_201_CREATED)
def create_risk_decision_endpoint(
    data: RiskDecisionCreate,
    db: Session = Depends(get_db),
):
    try:
        decision = create_risk_decision(
            db,
            data=data,
            decided_by_user_id=None,
        )
        return _commit_and_refresh(db, decision)
    except RiskDecisionBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
