import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel
from app.models.user import User


class AdminAuthorizationBusinessRuleError(ValueError):
    pass


def is_active_fixed_governance_member(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> bool:
    return db.scalar(
        select(CommitteeMember.id)
        .join(Committee, CommitteeMember.committee_id == Committee.id)
        .where(
            CommitteeMember.user_id == user_id,
            CommitteeMember.is_active.is_(True),
            Committee.is_active.is_(True),
            Committee.is_fixed.is_(True),
            Committee.authority_level.in_([AuthorityLevel.MIDDLE, AuthorityLevel.HIGH]),
        )
    ) is not None


def validate_admin_actor(
    db: Session,
    *,
    user_id: uuid.UUID | None,
) -> User:
    if user_id is None:
        raise AdminAuthorizationBusinessRuleError(
            "Admin operation requires an authenticated active governance user"
        )
    user = db.get(User, user_id)
    if user is None:
        raise AdminAuthorizationBusinessRuleError("Admin user does not exist")
    if not user.is_active:
        raise AdminAuthorizationBusinessRuleError("Admin user is inactive")
    if not is_active_fixed_governance_member(db, user_id=user_id):
        raise AdminAuthorizationBusinessRuleError(
            "User is not authorized to perform admin operations"
        )
    return user
