import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user
from app.core.database import get_db
from app.models.electronic_approval import ElectronicApproval
from app.models.enums import ElectronicApprovalTargetType
from app.models.user import User
from app.schemas.electronic_approval import (
    ElectronicApprovalCreate,
    ElectronicApprovalRead,
)
from app.services.electronic_approval_service import (
    ElectronicApprovalBusinessRuleError,
    create_electronic_approval,
    get_electronic_approval,
    list_electronic_approvals,
)

router = APIRouter(prefix="/electronic-approvals", tags=["electronic-approvals"])


def _require_current_user(current_user: User | None) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return current_user


def _commit_and_refresh(
    db: Session,
    approval: ElectronicApproval,
) -> ElectronicApproval:
    db.commit()
    db.refresh(approval)
    return approval


@router.post(
    "",
    response_model=ElectronicApprovalRead,
    status_code=status.HTTP_201_CREATED,
)
def create_electronic_approval_endpoint(
    data: ElectronicApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    actor = _require_current_user(current_user)
    try:
        approval = create_electronic_approval(
            db,
            data=data,
            approved_by_user_id=actor.id,
        )
        return _commit_and_refresh(db, approval)
    except ElectronicApprovalBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[ElectronicApprovalRead])
def list_electronic_approvals_endpoint(
    target_type: ElectronicApprovalTargetType | None = None,
    target_id: uuid.UUID | None = None,
    risk_record_id: uuid.UUID | None = None,
    approved_by_user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    actor = _require_current_user(current_user)
    try:
        return list_electronic_approvals(
            db,
            target_type=target_type,
            target_id=target_id,
            risk_record_id=risk_record_id,
            approved_by_user_id=approved_by_user_id,
            requested_by_user_id=actor.id,
        )
    except ElectronicApprovalBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{approval_id}", response_model=ElectronicApprovalRead)
def get_electronic_approval_endpoint(
    approval_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    actor = _require_current_user(current_user)
    try:
        approval = get_electronic_approval(
            db,
            approval_id=approval_id,
            requested_by_user_id=actor.id,
        )
    except ElectronicApprovalBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Electronic approval not found",
        )
    return approval
