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
