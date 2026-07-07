import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee, CommitteeMember
from app.models.user import User
from app.schemas.committee_member import CommitteeMemberCreate, CommitteeMemberUpdate

COMMITTEE_MEMBER_ENTITY_TYPE = "CommitteeMember"


class CommitteeMemberNotFoundError(ValueError):
    pass


class CommitteeMemberBusinessRuleError(ValueError):
    pass


def _committee_member_snapshot(member: CommitteeMember) -> dict[str, object]:
    return {
        "id": member.id,
        "committee_id": member.committee_id,
        "user_id": member.user_id,
        "role_label": member.role_label,
        "is_active": member.is_active,
    }


def _validate_role_label(role_label: str | None) -> None:
    if role_label is not None and not role_label.strip():
        raise CommitteeMemberBusinessRuleError("role_label must not be whitespace")


def _active_membership_exists(
    db: Session,
    *,
    committee_id: uuid.UUID,
    user_id: uuid.UUID,
    excluding_member_id: uuid.UUID | None = None,
) -> bool:
    statement = select(CommitteeMember.id).where(
        CommitteeMember.committee_id == committee_id,
        CommitteeMember.user_id == user_id,
        CommitteeMember.is_active.is_(True),
    )
    if excluding_member_id is not None:
        statement = statement.where(CommitteeMember.id != excluding_member_id)
    return db.scalar(statement) is not None


def create_committee_member(
    db: Session,
    *,
    data: CommitteeMemberCreate,
    changed_by_user_id: uuid.UUID | None = None,
) -> CommitteeMember:
    committee = db.get(Committee, data.committee_id)
    if committee is None:
        raise CommitteeMemberBusinessRuleError("Committee does not exist")
    if not committee.is_active:
        raise CommitteeMemberBusinessRuleError("Committee is inactive")

    user = db.get(User, data.user_id)
    if user is None:
        raise CommitteeMemberBusinessRuleError("User does not exist")
    if not user.is_active:
        raise CommitteeMemberBusinessRuleError("User is inactive")

    _validate_role_label(data.role_label)
    if _active_membership_exists(
        db,
        committee_id=data.committee_id,
        user_id=data.user_id,
    ):
        raise CommitteeMemberBusinessRuleError(
            "User already has an active membership in this committee"
        )

    member = CommitteeMember(
        committee_id=data.committee_id,
        user_id=data.user_id,
        role_label=data.role_label.strip() if data.role_label is not None else None,
        is_active=True,
    )
    db.add(member)
    db.flush()
    audit_service.log_entity_created(
        db,
        entity_type=COMMITTEE_MEMBER_ENTITY_TYPE,
        entity_id=member.id,
        created_by_user_id=changed_by_user_id,
        new_value=_committee_member_snapshot(member),
    )
    return member


def get_committee_member(
    db: Session,
    *,
    committee_member_id: uuid.UUID,
) -> CommitteeMember | None:
    return db.get(CommitteeMember, committee_member_id)


def list_committee_members(
    db: Session,
    *,
    committee_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[CommitteeMember]:
    statement = select(CommitteeMember).order_by(CommitteeMember.created_at.desc())
    if committee_id is not None:
        statement = statement.where(CommitteeMember.committee_id == committee_id)
    if user_id is not None:
        statement = statement.where(CommitteeMember.user_id == user_id)
    if not include_inactive:
        statement = statement.where(CommitteeMember.is_active.is_(True))
    return list(db.scalars(statement).all())


def update_committee_member(
    db: Session,
    *,
    committee_member_id: uuid.UUID,
    data: CommitteeMemberUpdate,
    changed_by_user_id: uuid.UUID | None = None,
    reason: str | None = None,
) -> CommitteeMember:
    member = get_committee_member(db, committee_member_id=committee_member_id)
    if member is None:
        raise CommitteeMemberNotFoundError("Committee member not found")

    update_data = data.model_dump(exclude_unset=True)
    if "role_label" in update_data:
        _validate_role_label(update_data["role_label"])
        if update_data["role_label"] is not None:
            update_data["role_label"] = update_data["role_label"].strip()
    if update_data.get("is_active") and _active_membership_exists(
        db,
        committee_id=member.committee_id,
        user_id=member.user_id,
        excluding_member_id=member.id,
    ):
        raise CommitteeMemberBusinessRuleError(
            "User already has an active membership in this committee"
        )
    if update_data.get("is_active"):
        committee = db.get(Committee, member.committee_id)
        if committee is None:
            raise CommitteeMemberBusinessRuleError("Committee does not exist")
        if not committee.is_active:
            raise CommitteeMemberBusinessRuleError("Committee is inactive")
        user = db.get(User, member.user_id)
        if user is None:
            raise CommitteeMemberBusinessRuleError("User does not exist")
        if not user.is_active:
            raise CommitteeMemberBusinessRuleError("User is inactive")

    for field_name, new_value in update_data.items():
        old_value = getattr(member, field_name)
        if old_value == new_value:
            continue
        setattr(member, field_name, new_value)
        audit_service.log_change(
            db,
            entity_type=COMMITTEE_MEMBER_ENTITY_TYPE,
            entity_id=member.id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            changed_by_user_id=changed_by_user_id,
            reason=reason,
        )

    db.add(member)
    db.flush()
    return member
