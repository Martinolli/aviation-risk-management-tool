import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.committee import CommitteeMember
from app.schemas.committee_member import (
    CommitteeMemberCreate,
    CommitteeMemberRead,
    CommitteeMemberUpdate,
)
from app.services.committee_member_service import (
    CommitteeMemberBusinessRuleError,
    CommitteeMemberNotFoundError,
    create_committee_member,
    get_committee_member,
    list_committee_members,
    update_committee_member,
)

router = APIRouter(prefix="/committee-members", tags=["committee-members"])


def _commit_and_refresh(db: Session, member: CommitteeMember) -> CommitteeMember:
    db.commit()
    db.refresh(member)
    return member


@router.get("", response_model=list[CommitteeMemberRead])
def list_committee_members_endpoint(
    committee_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    return list_committee_members(
        db,
        committee_id=committee_id,
        user_id=user_id,
        include_inactive=include_inactive,
    )


@router.get("/{committee_member_id}", response_model=CommitteeMemberRead)
def get_committee_member_endpoint(
    committee_member_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    member = get_committee_member(db, committee_member_id=committee_member_id)
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Committee member not found",
        )
    return member


@router.post("", response_model=CommitteeMemberRead, status_code=status.HTTP_201_CREATED)
def create_committee_member_endpoint(
    data: CommitteeMemberCreate,
    db: Session = Depends(get_db),
):
    try:
        return _commit_and_refresh(
            db,
            create_committee_member(db, data=data, changed_by_user_id=None),
        )
    except CommitteeMemberBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.patch("/{committee_member_id}", response_model=CommitteeMemberRead)
def update_committee_member_endpoint(
    committee_member_id: uuid.UUID,
    data: CommitteeMemberUpdate,
    db: Session = Depends(get_db),
):
    try:
        return _commit_and_refresh(
            db,
            update_committee_member(
                db,
                committee_member_id=committee_member_id,
                data=data,
                changed_by_user_id=None,
            ),
        )
    except CommitteeMemberNotFoundError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except CommitteeMemberBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
