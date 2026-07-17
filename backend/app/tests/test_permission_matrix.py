import json
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
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
        email=f"permission-matrix-{uuid.uuid4()}@example.com",
        display_name="Permission Matrix User",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def _get_matrix(client: TestClient, user: User):
    return client.get("/permission-matrix", headers=_headers(user))


def test_authenticated_active_user_can_retrieve_permission_matrix(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    response = _get_matrix(client, user)

    assert response.status_code == 200
    assert response.json()["policy_name"] == "Permission Matrix and Access Control Policy"


def test_unauthenticated_user_cannot_retrieve_permission_matrix(
    client: TestClient,
) -> None:
    response = client.get("/permission-matrix")

    assert response.status_code == 401


def test_inactive_user_cannot_retrieve_permission_matrix(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive_user = _create_user(db_session, is_active=False)
    db_session.commit()

    response = _get_matrix(client, inactive_user)

    assert response.status_code == 403


def test_permission_matrix_policy_version(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    assert _get_matrix(client, user).json()["policy_version"] == "0.1-mvp"


def test_permission_matrix_contains_required_governance_wording(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    payload = json.dumps(_get_matrix(client, user).json())

    assert "Permission Matrix" in payload
    assert "Access Control" in payload
    assert "Authority Level" in payload
    assert "LOW" in payload
    assert "MIDDLE" in payload
    assert "HIGH" in payload
    assert "Board of Origin" in payload
    assert "Fixed Governance Committee" in payload
    assert "SMS governance" in payload
    assert "Audit integrity" in payload


def test_permission_matrix_includes_required_sections(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    sections = {section["section"] for section in _get_matrix(client, user).json()["sections"]}

    assert "Risk Record Access" in sections
    assert "Committee Decision and Authority Level" in sections
    assert "Reports and Exports" in sections
    assert "Data Retention / Archive / Restore" in sections
    assert "Backup and Restore" in sections


def test_export_related_rules_mention_authorization_boundary(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    sections = _get_matrix(client, user).json()["sections"]
    reports = next(section for section in sections if section["section"] == "Reports and Exports")
    export_text = json.dumps(reports)

    assert "authorization boundary" in export_text
    assert "only risks readable by that user" in export_text


def test_archive_restore_rules_are_audited(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    sections = _get_matrix(client, user).json()["sections"]
    retention = next(
        section
        for section in sections
        if section["section"] == "Data Retention / Archive / Restore"
    )
    archive_restore_rules = [
        rule
        for rule in retention["rules"]
        if rule["capability"] in {"Archive Governed Record", "Restore Governed Record"}
    ]

    assert len(archive_restore_rules) == 2
    assert all(rule["audit_expected"] is True for rule in archive_restore_rules)


def test_permission_matrix_response_does_not_expose_secrets_or_database_url(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    payload = json.dumps(_get_matrix(client, user).json())

    assert settings.jwt_secret_key not in payload
    assert settings.database_url not in payload
    assert "jwt_secret" not in payload.lower()
    assert "database_url" not in payload.lower()
