import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, CommitteeType
from app.models.role import Role
from app.models.user import User
from app.services.bootstrap_service import (
    BOOTSTRAP_ADMIN_COMMITTEE_NAME,
    DEFAULT_ADMIN_ROLE_NAME,
    DEFAULT_AUDITOR_ROLE_NAME,
    DEFAULT_RISK_OWNER_ROLE_NAME,
    DEFAULT_SMS_MANAGER_ROLE_NAME,
    BootstrapBusinessRuleError,
    bootstrap_governance_admin,
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


def _bootstrap(db_session: Session) -> dict[str, object]:
    return bootstrap_governance_admin(
        db_session,
        admin_email=" Admin@Example.COM ",
        admin_display_name=" Admin User ",
    )


@pytest.mark.parametrize(
    ("email", "display_name"),
    [(" ", "Admin User"), ("admin@example.com", " ")],
)
def test_bootstrap_validates_required_admin_fields(
    db_session: Session,
    email: str,
    display_name: str,
) -> None:
    with pytest.raises(BootstrapBusinessRuleError):
        bootstrap_governance_admin(
            db_session,
            admin_email=email,
            admin_display_name=display_name,
        )


def test_bootstrap_creates_governance_admin_and_default_data(
    db_session: Session,
) -> None:
    result = _bootstrap(db_session)

    user = result["user"]
    committee = result["committee"]
    membership = result["membership"]
    assert user.email == "admin@example.com"
    assert user.display_name == "Admin User"
    assert user.is_active is True
    assert committee.name == BOOTSTRAP_ADMIN_COMMITTEE_NAME
    assert committee.is_fixed is True
    assert committee.authority_level == AuthorityLevel.MIDDLE
    assert membership.committee_id == committee.id
    assert membership.user_id == user.id
    assert membership.is_active is True
    assert membership.role_label == DEFAULT_ADMIN_ROLE_NAME
    assert result["created_user"] is True
    assert result["created_membership"] is True
    assert set(result["created_roles"]) == {
        DEFAULT_ADMIN_ROLE_NAME,
        DEFAULT_SMS_MANAGER_ROLE_NAME,
        DEFAULT_RISK_OWNER_ROLE_NAME,
        DEFAULT_AUDITOR_ROLE_NAME,
    }
    assert {role.name for role in result["roles"]} == set(result["created_roles"])
    assert db_session.scalar(select(func.count()).select_from(Committee)) == 5


def test_bootstrap_is_idempotent(db_session: Session) -> None:
    first_result = _bootstrap(db_session)
    second_result = _bootstrap(db_session)

    assert second_result["user"] is first_result["user"]
    assert second_result["created_user"] is False
    assert second_result["created_membership"] is False
    assert second_result["reactivated_membership"] is False
    assert second_result["created_roles"] == []
    assert db_session.scalar(select(func.count()).select_from(User)) == 1
    assert db_session.scalar(select(func.count()).select_from(Role)) == 4
    assert db_session.scalar(select(func.count()).select_from(CommitteeMember)) == 1


def test_bootstrap_reuses_active_existing_user_and_updates_blank_name(
    db_session: Session,
) -> None:
    user = User(email="admin@example.com", display_name="", is_active=True)
    db_session.add(user)
    db_session.flush()

    result = _bootstrap(db_session)

    assert result["user"] is user
    assert user.display_name == "Admin User"
    assert result["created_user"] is False


def test_bootstrap_rejects_inactive_existing_user(db_session: Session) -> None:
    db_session.add(
        User(email="admin@example.com", display_name="Former Admin", is_active=False)
    )
    db_session.flush()

    with pytest.raises(BootstrapBusinessRuleError, match="exists but is inactive"):
        _bootstrap(db_session)


def test_bootstrap_reactivates_existing_inactive_membership(db_session: Session) -> None:
    _bootstrap(db_session)
    membership = db_session.scalar(select(CommitteeMember))
    assert membership is not None
    membership.is_active = False
    db_session.flush()

    result = _bootstrap(db_session)

    assert result["membership"] is membership
    assert result["created_membership"] is False
    assert result["reactivated_membership"] is True
    assert membership.is_active is True
    assert db_session.scalar(select(func.count()).select_from(CommitteeMember)) == 1


def test_bootstrap_rejects_invalid_risk_management_committee(
    db_session: Session,
) -> None:
    db_session.add(
        Committee(
            name=BOOTSTRAP_ADMIN_COMMITTEE_NAME,
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
            is_fixed=False,
            is_active=True,
        )
    )
    db_session.flush()

    with pytest.raises(BootstrapBusinessRuleError, match="fixed MIDDLE"):
        _bootstrap(db_session)
