import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.committee import Committee
from app.models.user import User
from app.schemas.committee import (
    CommitteeArchive,
    CommitteeCreate,
    CommitteeRead,
    CommitteeUpdate,
)
from app.services.admin_authorization_service import (
    AdminAuthorizationBusinessRuleError,
    validate_admin_actor,
)
from app.services.committee_service import (
    CommitteeBusinessRuleError,
    CommitteeNotFoundError,
    archive_committee,
    create_committee,
    get_committee,
    list_committees,
    update_committee,
)

router = APIRouter(prefix="/committees", tags=["committees"])


def _commit_and_refresh(db: Session, committee: Committee) -> Committee:
    db.commit()
    db.refresh(committee)
    return committee


@router.get("", response_model=list[CommitteeRead])
def list_committee_endpoint(
    include_archived: bool = False,
    db: Session = Depends(get_db),
):
    return list_committees(db, include_archived=include_archived)


@router.get("/{committee_id}", response_model=CommitteeRead)
def get_committee_endpoint(
    committee_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    committee = get_committee(db, committee_id=committee_id)
    if committee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Committee not found"
        )
    return committee


@router.post("", response_model=CommitteeRead, status_code=status.HTTP_201_CREATED)
def create_committee_endpoint(
    data: CommitteeCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        validate_admin_actor(
            db, user_id=get_optional_current_user_id(current_user)
        )
        committee = create_committee(
            db,
            data=data,
            changed_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, committee)
    except (AdminAuthorizationBusinessRuleError, CommitteeBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{committee_id}", response_model=CommitteeRead)
def update_committee_endpoint(
    committee_id: uuid.UUID,
    data: CommitteeUpdate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        validate_admin_actor(
            db, user_id=get_optional_current_user_id(current_user)
        )
        committee = update_committee(
            db,
            committee_id=committee_id,
            data=data,
            changed_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, committee)
    except CommitteeNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Committee not found"
        ) from exc
    except (AdminAuthorizationBusinessRuleError, CommitteeBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/{committee_id}/archive", response_model=CommitteeRead)
def archive_committee_endpoint(
    committee_id: uuid.UUID,
    data: CommitteeArchive,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        validate_admin_actor(
            db, user_id=get_optional_current_user_id(current_user)
        )
        committee = archive_committee(
            db,
            committee_id=committee_id,
            changed_by_user_id=get_optional_current_user_id(current_user),
            archive_reason=data.archive_reason,
        )
        return _commit_and_refresh(db, committee)
    except CommitteeNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Committee not found"
        ) from exc
    except (AdminAuthorizationBusinessRuleError, CommitteeBusinessRuleError) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
