import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.risk import RiskAction
from app.models.user import User
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
    get_authorized_risk_action,
    get_my_risk_actions,
    list_authorized_risk_actions,
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
    include_completed: bool = True,
    include_cancelled: bool = True,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return list_authorized_risk_actions(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            risk_record_id=risk_record_id,
            include_completed=include_completed,
            include_cancelled=include_cancelled,
        )
    except RiskActionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RiskActionBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/my", response_model=list[RiskActionRead])
def get_my_risk_actions_endpoint(
    include_completed: bool = False,
    include_cancelled: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return get_my_risk_actions(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            include_completed=include_completed,
            include_cancelled=include_cancelled,
        )
    except RiskActionBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{risk_action_id}", response_model=RiskActionRead)
def get_risk_action_endpoint(
    risk_action_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        action = get_authorized_risk_action(
            db,
            risk_action_id=risk_action_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
        )
    except RiskActionBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
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
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        action = create_risk_action(
            db,
            data=data,
            created_by_user_id=get_optional_current_user_id(current_user),
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
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        action = update_risk_action(
            db,
            risk_action_id=risk_action_id,
            data=data,
            changed_by_user_id=get_optional_current_user_id(current_user),
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
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        action = complete_risk_action(
            db,
            risk_action_id=risk_action_id,
            changed_by_user_id=get_optional_current_user_id(current_user),
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
