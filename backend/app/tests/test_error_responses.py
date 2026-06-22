import uuid
from collections.abc import Generator

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app, create_app
from app.models.base import Base
from app.models.user import User


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


def _assert_error_shape(response, code: str) -> None:
    body = response.json()
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str)
    assert isinstance(body["error"]["details"], dict)


def test_unauthenticated_response_uses_standard_error_shape(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    _assert_error_shape(response, "UNAUTHENTICATED")


def test_not_found_response_uses_standard_error_shape(client: TestClient) -> None:
    response = client.get(f"/risks/{uuid.uuid4()}")

    assert response.status_code == 404
    _assert_error_shape(response, "NOT_FOUND")


def test_validation_response_includes_field_errors(client: TestClient) -> None:
    response = client.post("/auth/login", json={"email": "admin@example.com"})

    assert response.status_code == 422
    _assert_error_shape(response, "VALIDATION_ERROR")
    assert response.json()["error"]["details"]["errors"]


def test_forbidden_response_uses_standard_error_shape(
    client: TestClient, db_session: Session
) -> None:
    user = User(
        email="inactive-user@example.com",
        display_name="Inactive User",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.get("/auth/me", headers={"X-User-Id": str(user.id)})

    assert response.status_code == 403
    _assert_error_shape(response, "FORBIDDEN")


def test_business_rule_violation_uses_standard_error_shape(client: TestClient) -> None:
    response = client.post(
        "/risks",
        json={
            "problem_description": "No authenticated creator is provided.",
            "domain": "FLIGHT_TEST",
        },
    )

    assert response.status_code == 400
    _assert_error_shape(response, "BUSINESS_RULE_VIOLATION")


def test_structured_http_exception_detail_is_preserved() -> None:
    test_app = create_app()

    @test_app.get("/structured-error")
    def structured_error() -> None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "CUSTOM_CONFLICT",
                "message": "A custom conflict occurred.",
                "details": {"field": "name"},
            },
        )

    with TestClient(test_app) as client:
        response = client.get("/structured-error")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "CUSTOM_CONFLICT",
            "message": "A custom conflict occurred.",
            "details": {"field": "name"},
        }
    }


def test_unexpected_exception_uses_safe_internal_server_error_response() -> None:
    test_app = create_app()

    @test_app.get("/unexpected-error")
    def unexpected_error() -> None:
        raise RuntimeError("Sensitive implementation detail")

    with TestClient(test_app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "details": {},
        }
    }
