import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, CommitteeType
from app.models.user import User
from app.services.auth_service import create_access_token

ADMIN_ENDPOINTS = [
    "/admin/governance/users",
    "/admin/governance/committees",
    "/admin/governance/committee-members",
]


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name=f"Governance User {uuid.uuid4()}",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _committee_type(authority_level: AuthorityLevel) -> CommitteeType:
    return {
        AuthorityLevel.LOW: CommitteeType.OPERATIONAL_BOARD,
        AuthorityLevel.MIDDLE: CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        AuthorityLevel.HIGH: CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
    }[authority_level]


def _create_committee(
    db: Session,
    *,
    authority_level: AuthorityLevel,
    is_fixed: bool,
    is_active: bool = True,
) -> Committee:
    committee = Committee(
        name=f"{authority_level} Governance {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=_committee_type(authority_level),
        is_fixed=is_fixed,
        is_active=is_active,
    )
    db.add(committee)
    db.flush()
    return committee


def _authorize_user(
    db: Session,
    *,
    authority_level: AuthorityLevel,
    user_is_active: bool = True,
    membership_is_active: bool = True,
    committee_is_fixed: bool = True,
    role_label: str = "Governance Administrator",
) -> tuple[User, Committee, CommitteeMember]:
    user = _create_user(db, is_active=user_is_active)
    committee = _create_committee(
        db,
        authority_level=authority_level,
        is_fixed=committee_is_fixed,
    )
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        role_label=role_label,
        is_active=membership_is_active,
    )
    db.add(membership)
    db.commit()
    return user, committee, membership


def _auth_headers(user: User) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id=user.id)}",
    }


@pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
def test_admin_governance_endpoints_reject_unauthenticated_requests(
    client: TestClient,
    path: str,
) -> None:
    response = client.get(path)

    assert response.status_code == 400
    assert "authenticated active governance user" in response.json()["error"][
        "message"
    ]


@pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
def test_low_committee_member_cannot_read_admin_governance_data(
    client: TestClient,
    db_session: Session,
    path: str,
) -> None:
    user, _, _ = _authorize_user(
        db_session,
        authority_level=AuthorityLevel.LOW,
        committee_is_fixed=True,
    )

    response = client.get(path, headers=_auth_headers(user))

    assert response.status_code == 400
    assert response.json()["error"]["message"] == (
        "User is not authorized to perform admin operations"
    )


def test_system_admin_label_does_not_grant_admin_governance_access(
    client: TestClient,
    db_session: Session,
) -> None:
    user, _, _ = _authorize_user(
        db_session,
        authority_level=AuthorityLevel.LOW,
        committee_is_fixed=True,
        role_label="System Admin",
    )

    response = client.get(
        "/admin/governance/users",
        headers=_auth_headers(user),
    )

    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "authority_level",
    [AuthorityLevel.MIDDLE, AuthorityLevel.HIGH],
)
@pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
def test_fixed_middle_and_high_members_can_read_admin_governance_data(
    client: TestClient,
    db_session: Session,
    authority_level: AuthorityLevel,
    path: str,
) -> None:
    user, _, _ = _authorize_user(
        db_session,
        authority_level=authority_level,
    )

    response = client.get(path, headers=_auth_headers(user))

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
def test_inactive_user_cannot_read_admin_governance_data(
    client: TestClient,
    db_session: Session,
    path: str,
) -> None:
    user, _, _ = _authorize_user(
        db_session,
        authority_level=AuthorityLevel.MIDDLE,
        user_is_active=False,
    )

    response = client.get(path, headers=_auth_headers(user))

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "User is inactive"


@pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
def test_inactive_membership_cannot_read_admin_governance_data(
    client: TestClient,
    db_session: Session,
    path: str,
) -> None:
    user, _, _ = _authorize_user(
        db_session,
        authority_level=AuthorityLevel.MIDDLE,
        membership_is_active=False,
    )

    response = client.get(path, headers=_auth_headers(user))

    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]["message"]


@pytest.mark.parametrize(
    "authority_level",
    [AuthorityLevel.MIDDLE, AuthorityLevel.HIGH],
)
@pytest.mark.parametrize("path", ADMIN_ENDPOINTS)
def test_non_fixed_middle_and_high_membership_does_not_authorize_access(
    client: TestClient,
    db_session: Session,
    authority_level: AuthorityLevel,
    path: str,
) -> None:
    user, _, _ = _authorize_user(
        db_session,
        authority_level=authority_level,
        committee_is_fixed=False,
    )

    response = client.get(path, headers=_auth_headers(user))

    assert response.status_code == 400
    assert "not authorized" in response.json()["error"]["message"]


def test_authorized_admin_governance_responses_include_expected_data(
    client: TestClient,
    db_session: Session,
) -> None:
    admin, _, _ = _authorize_user(
        db_session,
        authority_level=AuthorityLevel.MIDDLE,
    )
    listed_user = _create_user(db_session, is_active=False)
    listed_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.HIGH,
        is_fixed=True,
    )
    listed_membership = CommitteeMember(
        committee_id=listed_committee.id,
        user_id=listed_user.id,
        role_label="Executive Observer",
        is_active=False,
    )
    db_session.add(listed_membership)
    db_session.commit()
    headers = _auth_headers(admin)

    users_response = client.get(
        "/admin/governance/users?include_inactive=true",
        headers=headers,
    )
    committees_response = client.get(
        "/admin/governance/committees?include_archived=true",
        headers=headers,
    )
    memberships_response = client.get(
        "/admin/governance/committee-members?include_inactive=true",
        headers=headers,
    )

    assert users_response.status_code == 200
    assert str(listed_user.id) in {item["id"] for item in users_response.json()}
    committees = committees_response.json()
    assert committees_response.status_code == 200
    assert any(
        item["id"] == str(listed_committee.id)
        and item["authority_level"] == "HIGH"
        for item in committees
    )
    memberships = memberships_response.json()
    assert memberships_response.status_code == 200
    assert any(
        item["id"] == str(listed_membership.id)
        and item["role_label"] == "Executive Observer"
        and item["is_active"] is False
        for item in memberships
    )
