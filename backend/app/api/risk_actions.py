import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.risk import RiskAction
from app.schemas.risk_action import (
    RiskActionComplete,
    RiskActionCreate,
    RiskActionRead,
    RiskActionUpdate,
)
from app.services.risk_action_service import (
    RiskActionBusinessRuleError,
    RiskActionNotFoundError,
    complete_risk_action,
    create_risk_action,
    get_risk_action,
    list_risk_actions,
    update_risk_action,
)

router = APIRouter(prefix="/risk-actions", tags=["risk-actions"])


def _commit_and_refresh(db: Session, risk_action: RiskAction) -> RiskAction:
    db.commit()
    db.refresh(risk_action)
    return risk_action


@router.get("", response_model=list[RiskActionRead])
def list_risk_actions_endpoint(
    risk_record_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
):
    return list_risk_actions(db, risk_record_id=risk_record_id)


@router.get("/{risk_action_id}", response_model=RiskActionRead)
def get_risk_action_endpoint(
    risk_action_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    action = get_risk_action(db, risk_action_id=risk_action_id)
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk action not found",
        )
    return action


@router.post("", response_model=RiskActionRead, status_code=status.HTTP_201_CREATED)
def create_risk_action_endpoint(
    data: RiskActionCreate,
    db: Session = Depends(get_db),
):
    try:
        action = create_risk_action(
            db,
            data=data,
            created_by_user_id=None,
        )
        return _commit_and_refresh(db, action)
    except RiskActionBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch("/{risk_action_id}", response_model=RiskActionRead)
def update_risk_action_endpoint(
    risk_action_id: uuid.UUID,
    data: RiskActionUpdate,
    db: Session = Depends(get_db),
):
    try:
        action = update_risk_action(
            db,
            risk_action_id=risk_action_id,
            data=data,
            changed_by_user_id=None,
        )
        return _commit_and_refresh(db, action)
    except RiskActionNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk action not found",
        ) from exc
    except RiskActionBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/{risk_action_id}/complete", response_model=RiskActionRead)
def complete_risk_action_endpoint(
    risk_action_id: uuid.UUID,
    data: RiskActionComplete,
    db: Session = Depends(get_db),
):
    try:
        action = complete_risk_action(
            db,
            risk_action_id=risk_action_id,
            changed_by_user_id=None,
            completion_notes=data.completion_notes,
        )
        return _commit_and_refresh(db, action)
    except RiskActionNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Risk action not found",
        ) from exc
    except RiskActionBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
