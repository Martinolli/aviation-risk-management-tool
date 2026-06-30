import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.committee import CommitteeRead
from app.schemas.committee_member import CommitteeMemberRead
from app.schemas.user import UserRead
from app.services.admin_authorization_service import (
    AdminAuthorizationBusinessRuleError,
    validate_admin_actor,
)
from app.services.committee_member_service import list_committee_members
from app.services.committee_service import list_committees
from app.services.user_service import list_users

router = APIRouter(prefix="/admin/governance", tags=["admin-governance"])


def _require_admin_actor(
    db: Session,
    *,
    current_user: User | None,
) -> None:
    try:
        validate_admin_actor(
            db,
            user_id=get_optional_current_user_id(current_user),
        )
    except AdminAuthorizationBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/users", response_model=list[UserRead])
def list_admin_governance_users_endpoint(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _require_admin_actor(db, current_user=current_user)
    return list_users(db, include_inactive=include_inactive)


@router.get("/committees", response_model=list[CommitteeRead])
def list_admin_governance_committees_endpoint(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _require_admin_actor(db, current_user=current_user)
    return list_committees(db, include_archived=include_archived)


@router.get("/committee-members", response_model=list[CommitteeMemberRead])
def list_admin_governance_committee_members_endpoint(
    committee_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _require_admin_actor(db, current_user=current_user)
    return list_committee_members(
        db,
        committee_id=committee_id,
        user_id=user_id,
        include_inactive=include_inactive,
    )
