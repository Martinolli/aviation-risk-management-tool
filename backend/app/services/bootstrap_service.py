from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel
from app.models.role import Role
from app.models.user import User
from app.services.security_service import hash_password
from app.services.seed_service import seed_default_committees

DEFAULT_ADMIN_ROLE_NAME = "Governance Administrator"
DEFAULT_SMS_MANAGER_ROLE_NAME = "SMS Manager"
DEFAULT_RISK_OWNER_ROLE_NAME = "Risk Owner"
DEFAULT_AUDITOR_ROLE_NAME = "Auditor"

BOOTSTRAP_ADMIN_COMMITTEE_NAME = "Risk Management Committee"
DEFAULT_ROLE_NAMES = [
    DEFAULT_ADMIN_ROLE_NAME,
    DEFAULT_SMS_MANAGER_ROLE_NAME,
    DEFAULT_RISK_OWNER_ROLE_NAME,
    DEFAULT_AUDITOR_ROLE_NAME,
]


class BootstrapBusinessRuleError(ValueError):
    pass


def bootstrap_governance_admin(
    db: Session,
    *,
    admin_email: str,
    admin_display_name: str,
    admin_password: str | None = None,
) -> dict[str, object]:
    normalized_email = admin_email.strip().lower()
    display_name = admin_display_name.strip()
    if not normalized_email:
        raise BootstrapBusinessRuleError("Bootstrap admin email must not be empty")
    if not display_name:
        raise BootstrapBusinessRuleError("Bootstrap admin display name must not be empty")

    seed_default_committees(db)

    roles: list[Role] = []
    created_roles: list[str] = []
    for role_name in DEFAULT_ROLE_NAMES:
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name, is_active=True)
            db.add(role)
            db.flush()
            created_roles.append(role_name)
        roles.append(role)

    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    created_user = user is None
    if user is None:
        user = User(
            email=normalized_email,
            display_name=display_name,
            password_hash=(
                hash_password(admin_password) if admin_password is not None else None
            ),
            is_active=True,
        )
        db.add(user)
        db.flush()
    else:
        if not user.is_active:
            raise BootstrapBusinessRuleError("Bootstrap admin user exists but is inactive")
        if not (user.display_name or "").strip():
            user.display_name = display_name
            db.add(user)
            db.flush()
        if admin_password is not None and not user.password_hash:
            user.password_hash = hash_password(admin_password)
            db.add(user)
            db.flush()

    committee = db.scalar(
        select(Committee).where(Committee.name == BOOTSTRAP_ADMIN_COMMITTEE_NAME)
    )
    if committee is None:
        raise BootstrapBusinessRuleError("Risk Management Committee does not exist")
    if not committee.is_fixed or committee.authority_level != AuthorityLevel.MIDDLE:
        raise BootstrapBusinessRuleError(
            "Risk Management Committee must be a fixed MIDDLE authority committee"
        )

    membership = db.scalar(
        select(CommitteeMember).where(
            CommitteeMember.committee_id == committee.id,
            CommitteeMember.user_id == user.id,
        )
    )
    created_membership = membership is None
    reactivated_membership = False
    if membership is None:
        membership = CommitteeMember(
            committee_id=committee.id,
            user_id=user.id,
            role_label=DEFAULT_ADMIN_ROLE_NAME,
            is_active=True,
        )
        db.add(membership)
        db.flush()
    elif not membership.is_active:
        membership.is_active = True
        if not membership.role_label:
            membership.role_label = DEFAULT_ADMIN_ROLE_NAME
        db.add(membership)
        db.flush()
        reactivated_membership = True

    return {
        "user": user,
        "committee": committee,
        "membership": membership,
        "roles": roles,
        "created_user": created_user,
        "created_roles": created_roles,
        "created_membership": created_membership,
        "reactivated_membership": reactivated_membership,
    }
