import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import AuditAction


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


def _create_audit_log(
    db_session: Session,
    *,
    entity_type: str = "RiskRecord",
    action: AuditAction = AuditAction.CREATE,
    changed_at: datetime | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=uuid.uuid4(),
        action=action,
        field_name=None,
        old_value=None,
        new_value={"created": True},
        changed_by_user_id=None,
        changed_at=changed_at or datetime.now(timezone.utc),
        reason=None,
    )
    db_session.add(audit_log)
    db_session.commit()
    db_session.refresh(audit_log)
    return audit_log


def test_get_audit_logs_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_audit_log(db_session)

    response = client.get("/audit-logs")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_audit_log_returns_audit_log(
    client: TestClient,
    db_session: Session,
) -> None:
    audit_log = _create_audit_log(db_session)

    response = client.get(f"/audit-logs/{audit_log.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(audit_log.id)


def test_get_unknown_audit_log_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/audit-logs/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_audit_logs_filtered_by_entity_type(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_audit_log(db_session, entity_type="RiskRecord")
    _create_audit_log(db_session, entity_type="Committee")

    response = client.get("/audit-logs?entity_type=RiskRecord")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["entity_type"] == "RiskRecord"


def test_get_audit_logs_filtered_by_action(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_audit_log(db_session, action=AuditAction.CREATE)
    _create_audit_log(db_session, action=AuditAction.UPDATE)

    response = client.get("/audit-logs?action=CREATE")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["action"] == "CREATE"


def test_get_audit_logs_with_limit_returns_one_item(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_audit_log(db_session)
    _create_audit_log(db_session)

    response = client.get("/audit-logs?limit=1")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_audit_logs_with_offset_skips_first_item(
    client: TestClient,
    db_session: Session,
) -> None:
    now = datetime.now(timezone.utc)
    older = _create_audit_log(db_session, changed_at=now - timedelta(minutes=1))
    newest = _create_audit_log(db_session, changed_at=now)

    response = client.get("/audit-logs?offset=1")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(older.id)
    assert body[0]["id"] != str(newest.id)


def test_get_audit_logs_with_limit_zero_returns_http_400(
    client: TestClient,
) -> None:
    response = client.get("/audit-logs?limit=0")

    assert response.status_code == 400


def test_get_audit_logs_with_negative_offset_returns_http_400(
    client: TestClient,
) -> None:
    response = client.get("/audit-logs?offset=-1")

    assert response.status_code == 400
