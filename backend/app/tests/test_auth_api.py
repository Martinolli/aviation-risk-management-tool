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
from app.services.security_service import hash_password


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
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


def _user(
    db_session: Session,
    *,
    password: str | None = "StrongPassword123!",
    is_active: bool = True,
) -> User:
    user = User(
        email=f"auth-{uuid.uuid4()}@example.com",
        display_name="Auth API User",
        password_hash=hash_password(password) if password else None,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_login_returns_token_and_token_authenticates_protected_request(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _user(db_session)
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "StrongPassword123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["id"] == str(user.id)
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    protected_response = client.post(
        "/risks",
        json={"problem_description": "Token-authenticated risk", "domain": "FLIGHT_TEST"},
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert protected_response.status_code == 201
    assert protected_response.json()["created_by_user_id"] == str(user.id)


@pytest.mark.parametrize("password", ["WrongPassword123!", "StrongPassword123!"])
def test_login_rejects_invalid_or_unknown_credentials(
    client: TestClient,
    db_session: Session,
    password: str,
) -> None:
    user = _user(db_session)
    email = user.email if password != "StrongPassword123!" else "unknown@example.com"

    response = client.post("/auth/login", json={"email": email, "password": password})

    assert response.status_code == 401


def test_login_rejects_inactive_and_passwordless_users(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive_user = _user(db_session, is_active=False)
    passwordless_user = _user(db_session, password=None)

    inactive_response = client.post(
        "/auth/login",
        json={"email": inactive_user.email, "password": "StrongPassword123!"},
    )
    passwordless_response = client.post(
        "/auth/login",
        json={"email": passwordless_user.email, "password": "StrongPassword123!"},
    )

    assert inactive_response.status_code == 403
    assert passwordless_response.status_code == 401


def test_login_rejects_malformed_request(client: TestClient) -> None:
    assert client.post("/auth/login", json={"email": "admin@example.com"}).status_code == 422


def _login_headers(client: TestClient, user: User) -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_auth_me_returns_bearer_user_without_password_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _user(db_session)

    response = client.get("/auth/me", headers=_login_headers(client, user))

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert response.json()["email"] == user.email
    assert response.json()["display_name"] == user.display_name
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_auth_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert response.json()["error"]["message"] == "Authentication required"


def test_auth_me_supports_temporary_x_user_id_fallback(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _user(db_session, password=None)

    response = client.get("/auth/me", headers={"X-User-Id": str(user.id)})

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_auth_me_bearer_token_takes_precedence_over_x_user_id(
    client: TestClient,
    db_session: Session,
) -> None:
    token_user = _user(db_session)
    header_user = _user(db_session, password=None)
    headers = _login_headers(client, token_user)
    headers["X-User-Id"] = str(header_user.id)

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == str(token_user.id)


def test_auth_me_rejects_invalid_and_inactive_bearer_users(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _user(db_session)
    token = _login_headers(client, user)["Authorization"]
    user.is_active = False
    db_session.commit()

    invalid_response = client.get(
        "/auth/me", headers={"Authorization": "Bearer invalid"}
    )
    inactive_response = client.get("/auth/me", headers={"Authorization": token})

    assert invalid_response.status_code == 401
    assert inactive_response.status_code == 403


def test_jwt_authenticates_governance_admin_write(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _user(db_session)
    committee = Committee(
        name=f"Governance {uuid.uuid4()}",
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        is_fixed=True,
        is_active=True,
    )
    db_session.add(committee)
    db_session.flush()
    db_session.add(
        CommitteeMember(committee_id=committee.id, user_id=admin.id, is_active=True)
    )
    db_session.commit()

    response = client.post(
        "/roles",
        json={"name": f"JWT Admin Role {uuid.uuid4()}"},
        headers=_login_headers(client, admin),
    )

    assert response.status_code == 201
