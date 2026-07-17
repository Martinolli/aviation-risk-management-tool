import json
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.user import User
from app.services.auth_service import create_access_token


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, autoflush=False, autocommit=False)() as session:
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
        email=f"retention-{uuid.uuid4()}@example.com",
        display_name="Retention Policy User",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def _get_policy(client: TestClient, user: User):
    return client.get("/data-retention-policy", headers=_headers(user))


def test_authenticated_user_can_retrieve_data_retention_policy(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    response = _get_policy(client, user)

    assert response.status_code == 200
    assert response.json()["policy_name"] == "Data Retention and Archive Policy"


def test_unauthenticated_user_cannot_retrieve_data_retention_policy(
    client: TestClient,
) -> None:
    response = client.get("/data-retention-policy")

    assert response.status_code == 401


def test_policy_contains_mvp_version_and_draft_status(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    body = _get_policy(client, user).json()

    assert body["policy_version"] == "0.1-mvp"
    assert body["effective_status"] == "Draft for SMS governance review"


def test_policy_includes_no_hard_delete_principle_or_wording(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    payload = json.dumps(_get_policy(client, user).json())

    assert "No Hard Delete" in payload


def test_policy_includes_required_record_types(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    record_types = {
        item["record_type"] for item in _get_policy(client, user).json()["items"]
    }

    assert "Risk Records" in record_types
    assert "Risk Assessments" in record_types
    assert "Risk Decisions" in record_types
    assert "Mitigation Actions" in record_types
    assert "Monitoring Reviews" in record_types
    assert "Evidence Uploads" in record_types
    assert "Generated Reports" in record_types
    assert "Audit Logs" in record_types
    assert "Committee Meetings and Minutes" in record_types
    assert "User and Role Records" in record_types
    assert "Backups" in record_types
    assert "Exports" in record_types


def test_policy_marks_core_governance_records_as_no_hard_delete(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    no_hard_delete_types = set(
        _get_policy(client, user).json()["no_hard_delete_record_types"]
    )

    assert "Audit Logs" in no_hard_delete_types
    assert "Risk Records" in no_hard_delete_types
    assert "Evidence Uploads" in no_hard_delete_types


def test_policy_mentions_legal_investigation_hold(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    payload = json.dumps(_get_policy(client, user).json())

    assert "Legal / Investigation Hold" in payload
    assert "legal" in payload.lower()
    assert "investigation" in payload.lower()


def test_endpoint_response_does_not_expose_secrets_or_database_url(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    payload = json.dumps(_get_policy(client, user).json())

    assert settings.jwt_secret_key not in payload
    assert settings.database_url not in payload
    assert "jwt_secret" not in payload.lower()
    assert "database_url" not in payload.lower()
