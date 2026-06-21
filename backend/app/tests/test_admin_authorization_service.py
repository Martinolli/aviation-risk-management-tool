import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, CommitteeType
from app.models.user import User
from app.services.admin_authorization_service import (
    AdminAuthorizationBusinessRuleError,
    is_active_fixed_governance_member,
    validate_admin_actor,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


def _user(db: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"admin-{uuid.uuid4()}@example.com",
        display_name="Admin Candidate",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _committee(
    db: Session,
    *,
    authority_level: AuthorityLevel,
    is_fixed: bool,
    is_active: bool = True,
) -> Committee:
    committee = Committee(
        name=f"Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=is_fixed,
        is_active=is_active,
    )
    db.add(committee)
    db.flush()
    return committee


def _membership(
    db: Session,
    *,
    committee: Committee,
    user: User,
    is_active: bool = True,
) -> CommitteeMember:
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        is_active=is_active,
    )
    db.add(membership)
    db.flush()
    return membership


@pytest.mark.parametrize("user_id", [None, uuid.uuid4()])
def test_validate_admin_actor_rejects_missing_or_unknown_user(
    db_session: Session,
    user_id: uuid.UUID | None,
) -> None:
    with pytest.raises(AdminAuthorizationBusinessRuleError):
        validate_admin_actor(db_session, user_id=user_id)


def test_validate_admin_actor_rejects_inactive_user(db_session: Session) -> None:
    with pytest.raises(AdminAuthorizationBusinessRuleError):
        validate_admin_actor(db_session, user_id=_user(db_session, is_active=False).id)


@pytest.mark.parametrize(
    "authority_level,is_fixed,committee_active,membership_active",
    [
        (AuthorityLevel.LOW, False, True, True),
        (AuthorityLevel.MIDDLE, True, False, True),
        (AuthorityLevel.MIDDLE, True, True, False),
        (AuthorityLevel.MIDDLE, False, True, True),
    ],
)
def test_validate_admin_actor_rejects_non_governance_memberships(
    db_session: Session,
    authority_level: AuthorityLevel,
    is_fixed: bool,
    committee_active: bool,
    membership_active: bool,
) -> None:
    user = _user(db_session)
    committee = _committee(
        db_session,
        authority_level=authority_level,
        is_fixed=is_fixed,
        is_active=committee_active,
    )
    _membership(db_session, committee=committee, user=user, is_active=membership_active)

    assert not is_active_fixed_governance_member(db_session, user_id=user.id)
    with pytest.raises(AdminAuthorizationBusinessRuleError):
        validate_admin_actor(db_session, user_id=user.id)


@pytest.mark.parametrize("authority_level", [AuthorityLevel.MIDDLE, AuthorityLevel.HIGH])
def test_validate_admin_actor_accepts_fixed_governance_members(
    db_session: Session,
    authority_level: AuthorityLevel,
) -> None:
    user = _user(db_session)
    committee = _committee(
        db_session,
        authority_level=authority_level,
        is_fixed=True,
    )
    _membership(db_session, committee=committee, user=user)

    assert is_active_fixed_governance_member(db_session, user_id=user.id)
    assert validate_admin_actor(db_session, user_id=user.id) is user


def test_validate_admin_actor_rejects_active_user_without_membership(
    db_session: Session,
) -> None:
    with pytest.raises(AdminAuthorizationBusinessRuleError):
        validate_admin_actor(db_session, user_id=_user(db_session).id)
