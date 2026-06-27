import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel
from app.models.user import User
from app.schemas.committee_member import CommitteeMemberCreate, CommitteeMemberUpdate
from app.schemas.user import UserCreate, UserUpdate
from app.services.committee_member_service import (
    create_committee_member,
    update_committee_member,
)
from app.services.security_service import verify_password
from app.services.user_service import create_user, update_user


class TestAccessSeedError(ValueError):
    __test__ = False

    pass


TEST_ACCESS_PROFILES: list[dict[str, Any]] = [
    {
        "display_name": "Joao Bosco Martinolli",
        "email": "joao.bosco@calidus.ae",
        "password": "ChangeMe123!",
        "committee_name": "Risk Management Committee",
        "Authority Level": "MIDDLE",
        "committee_role_label": "Governance Administrator",
        "role_function": (
            "System administration, bootstrap, user / committee management; "
            "risk governance administration"
        ),
        "expected_permissions": [
            "System administration",
            "Bootstrap",
            "User / committee management",
            "Full governance risk visibility",
            "Review escalated risks",
        ],
        "notes": [
            "System administration and governance administration remain distinct responsibilities",
        ],
        "is_system_admin": True,
    },
    {
        "display_name": "Kevin Rooney",
        "email": "kevin.rooney@calidus.ae",
        "password": "ChangeMe123!",
        "committee_name": "Aircraft Safety Committee - Engineering Board",
        "Authority Level": "LOW",
        "committee_role_label": "Committee Chairman",
        "role_function": "Requirements Management Specialist",
        "expected_permissions": [
            "Review Aircraft / Engineering risks",
            "Record operational board decisions",
            "Accept tolerable residual risk",
        ],
        "notes": [
            "Closes risks only when residual risk is tolerable and actions are complete",
        ],
        "is_system_admin": False,
    },
    {
        "display_name": "Gulzar Hussain",
        "email": "gulzar.hussain@calidus.ae",
        "password": "ChangeMe123!",
        "committee_name": (
            "Industrial Safety Committee - Quality, Manufacturing, Production, "
            "Supply Chain, OHSE"
        ),
        "Authority Level": "LOW",
        "committee_role_label": "Committee Member",
        "role_function": "Aircraft Maintenance Technician",
        "expected_permissions": [
            "Review Industrial / Quality risks",
            "Record operational board decisions",
            "Accept tolerable residual risk",
            "Close risks only when residual risk is tolerable and actions are complete",
        ],
        "notes": [
            "Should not approve Flight Test risks unless also member of that committee",
        ],
        "is_system_admin": False,
    },
    {
        "display_name": "Joao Victor De Souza",
        "email": "joao.desouza@calidus.ae",
        "password": "ChangeMe123!",
        "committee_name": "Flight Test Safety Committee - Operation",
        "Authority Level": "LOW",
        "committee_role_label": "Committee Chairman",
        "role_function": "Flight Test Instrumentation Manager",
        "expected_permissions": [
            "Review Flight Test risks",
            "Record operational board decisions",
            "Accept tolerable residual risk",
        ],
        "notes": [
            "Closes risks only when residual risk is tolerable and actions are complete",
        ],
        "is_system_admin": False,
    },
    {
        "display_name": "Andres Samper",
        "email": "andres.samper@calidus.ae",
        "password": "ChangeMe123!",
        "committee_name": "Risk Management Committee",
        "Authority Level": "MIDDLE",
        "committee_role_label": "Committee Member",
        "role_function": "Director of Airworthiness and Certification",
        "expected_permissions": [
            "Review escalated risks",
            "Accept residual risks",
            "Escalate to executive committee when needed",
        ],
        "notes": [],
        "is_system_admin": False,
    },
    {
        "display_name": "Celso Cobra",
        "email": "celso.cobra@calaero.ae",
        "password": "ChangeMe123!",
        "committee_name": "Risk Management Committee",
        "Authority Level": "MIDDLE",
        "committee_role_label": "Committee Chairman",
        "role_function": "Director of QHSE",
        "expected_permissions": [
            "Review escalated risks",
            "Accept residual risks",
            "Escalate to executive committee when necessary",
        ],
        "notes": [],
        "is_system_admin": False,
    },
]


def seed_test_access_profiles(
    db: Session,
    *,
    password: str,
    changed_by_user_id: uuid.UUID | None = None,
    dry_run: bool = False,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "created_users": 0,
        "updated_users": 0,
        "existing_users": 0,
        "created_memberships": 0,
        "updated_memberships": 0,
        "existing_memberships": 0,
        "profiles": [],
        "dry_run": dry_run,
        "admin_role_status": "not_assigned",
    }

    profile_summaries: list[dict[str, object]] = []
    for profile in TEST_ACCESS_PROFILES:
        user, user_status = _ensure_user(
            db,
            profile=profile,
            password=password,
            changed_by_user_id=changed_by_user_id,
        )
        summary[f"{user_status}_users"] = int(summary[f"{user_status}_users"]) + 1

        committee_name = profile["committee_name"]
        membership_status = "not_applicable"
        if committee_name is not None:
            membership_status = _ensure_committee_membership(
                db,
                committee_name=str(committee_name),
                authority_level=str(profile["Authority Level"]),
                user_id=user.id,
                role_label=str(profile["committee_role_label"]),
                changed_by_user_id=changed_by_user_id,
            )
            summary[f"{membership_status}_memberships"] = (
                int(summary[f"{membership_status}_memberships"]) + 1
            )

        profile_summaries.append(
            {
                "email": profile["email"],
                "display_name": profile["display_name"],
                "is_system_admin": profile["is_system_admin"],
                "committee": committee_name,
                "Authority Level": profile["Authority Level"],
                "membership_status": membership_status,
                "user_status": user_status,
            }
        )

        if profile["is_system_admin"]:
            summary["admin_role_status"] = "profiled"

    summary["profiles"] = profile_summaries
    return summary


def _ensure_user(
    db: Session,
    *,
    profile: dict[str, Any],
    password: str,
    changed_by_user_id: uuid.UUID | None,
) -> tuple[User, str]:
    email = str(profile["email"]).strip()
    display_name = str(profile["display_name"]).strip()
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower()))

    if user is None:
        user = create_user(
            db,
            data=UserCreate(
                email=email,
                display_name=display_name,
                password=password,
            ),
            changed_by_user_id=changed_by_user_id,
        )
        return user, "created"

    needs_password_update = (
        bool(password)
        and (user.password_hash is None or not verify_password(password, user.password_hash))
    )
    update_data: dict[str, object] = {}
    if user.display_name != display_name:
        update_data["display_name"] = display_name
    if not user.is_active:
        update_data["is_active"] = True
    if needs_password_update:
        update_data["password"] = password

    if update_data:
        user = update_user(
            db,
            user_id=user.id,
            data=UserUpdate(**update_data),
            changed_by_user_id=changed_by_user_id,
            reason="Seed test access profiles",
        )
        return user, "updated"

    return user, "existing"


def _ensure_committee_membership(
    db: Session,
    *,
    committee_name: str,
    authority_level: str,
    user_id: uuid.UUID,
    role_label: str,
    changed_by_user_id: uuid.UUID | None,
) -> str:
    committee = db.scalar(select(Committee).where(Committee.name == committee_name))
    if committee is None:
        raise TestAccessSeedError(f"Required committee does not exist: {committee_name}")
    if not committee.is_active:
        raise TestAccessSeedError(f"Required committee is inactive: {committee_name}")

    expected_authority_level = AuthorityLevel(authority_level)
    if committee.authority_level != expected_authority_level:
        raise TestAccessSeedError(
            "Committee Authority Level mismatch for "
            f"{committee_name}: expected {expected_authority_level.value}, "
            f"found {committee.authority_level.value}"
        )

    membership = db.scalar(
        select(CommitteeMember).where(
            CommitteeMember.committee_id == committee.id,
            CommitteeMember.user_id == user_id,
            CommitteeMember.is_active.is_(True),
        )
    )
    if membership is None:
        create_committee_member(
            db,
            data=CommitteeMemberCreate(
                committee_id=committee.id,
                user_id=user_id,
                role_label=role_label,
            ),
            changed_by_user_id=changed_by_user_id,
        )
        return "created"

    if membership.role_label != role_label:
        update_committee_member(
            db,
            committee_member_id=membership.id,
            data=CommitteeMemberUpdate(role_label=role_label),
            changed_by_user_id=changed_by_user_id,
            reason="Seed test access profiles",
        )
        return "updated"

    return "existing"
