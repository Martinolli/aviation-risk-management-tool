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
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuditAction, AuthorityLevel, CommitteeType, RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus
from app.models.risk import RiskRecord
from app.models.user import User


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
    entity_id: uuid.UUID | None = None,
    action: AuditAction = AuditAction.CREATE,
    changed_at: datetime | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id or uuid.uuid4(),
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


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Audit Reader",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_risk_record(db_session: Session, *, creator: User) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


@pytest.fixture()
def governance_reader(db_session: Session) -> User:
    user = _create_user(db_session)
    committee = Committee(
        name=f"Governance {uuid.uuid4()}",
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        is_fixed=True,
        is_active=True,
    )
    db_session.add(committee)
    db_session.commit()
    db_session.refresh(committee)
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        is_active=True,
    )
    db_session.add(membership)
    db_session.commit()
    return user


def test_get_audit_logs_returns_list(
    client: TestClient,
    db_session: Session,
    governance_reader: User,
) -> None:
    _create_audit_log(db_session)

    response = client.get("/audit-logs", headers={"X-User-Id": str(governance_reader.id)})

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_audit_log_returns_audit_log(
    client: TestClient,
    db_session: Session,
    governance_reader: User,
) -> None:
    audit_log = _create_audit_log(db_session)

    response = client.get(
        f"/audit-logs/{audit_log.id}",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(audit_log.id)


def test_get_unknown_audit_log_returns_http_404(
    client: TestClient, governance_reader: User
) -> None:
    response = client.get(
        f"/audit-logs/{uuid.uuid4()}",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 404


def test_get_audit_logs_filtered_by_entity_type(
    client: TestClient,
    db_session: Session,
    governance_reader: User,
) -> None:
    _create_audit_log(db_session, entity_type="RiskRecord")
    _create_audit_log(db_session, entity_type="Committee")

    response = client.get(
        "/audit-logs?entity_type=RiskRecord",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["entity_type"] == "RiskRecord"


def test_get_audit_logs_filtered_by_action(
    client: TestClient,
    db_session: Session,
    governance_reader: User,
) -> None:
    _create_audit_log(db_session, action=AuditAction.CREATE)
    _create_audit_log(db_session, action=AuditAction.UPDATE)

    response = client.get(
        "/audit-logs?action=CREATE",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["action"] == "CREATE"


def test_get_audit_logs_with_limit_returns_one_item(
    client: TestClient,
    db_session: Session,
    governance_reader: User,
) -> None:
    _create_audit_log(db_session)
    _create_audit_log(db_session)

    response = client.get(
        "/audit-logs?limit=1",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_audit_logs_with_offset_skips_first_item(
    client: TestClient,
    db_session: Session,
    governance_reader: User,
) -> None:
    now = datetime.now(timezone.utc)
    older = _create_audit_log(db_session, changed_at=now - timedelta(minutes=1))
    newest = _create_audit_log(db_session, changed_at=now)

    response = client.get(
        "/audit-logs?offset=1",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(older.id)
    assert body[0]["id"] != str(newest.id)


def test_get_audit_logs_with_limit_zero_returns_http_400(
    client: TestClient,
    governance_reader: User,
) -> None:
    response = client.get(
        "/audit-logs?limit=0",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 400


def test_get_audit_logs_with_negative_offset_returns_http_400(
    client: TestClient,
    governance_reader: User,
) -> None:
    response = client.get(
        "/audit-logs?offset=-1",
        headers={"X-User-Id": str(governance_reader.id)},
    )

    assert response.status_code == 400


def test_audit_log_endpoints_require_active_user(
    client: TestClient,
    db_session: Session,
) -> None:
    audit_log = _create_audit_log(db_session)
    inactive_user = _create_user(db_session, is_active=False)

    assert client.get("/audit-logs").status_code == 400
    assert client.get(f"/audit-logs/{audit_log.id}").status_code == 400
    assert client.get(
        "/audit-logs", headers={"X-User-Id": str(uuid.uuid4())}
    ).status_code == 401
    assert client.get(
        f"/audit-logs/{audit_log.id}",
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403


def test_risk_audit_api_access_filters_unrelated_users(
    client: TestClient,
    db_session: Session,
    governance_reader: User,
) -> None:
    creator = _create_user(db_session)
    unrelated_user = _create_user(db_session)
    risk_record = _create_risk_record(db_session, creator=creator)
    audit_log = _create_audit_log(
        db_session,
        entity_type="RiskRecord",
        entity_id=risk_record.id,
    )

    creator_headers = {"X-User-Id": str(creator.id)}
    assert client.get(
        f"/audit-logs?entity_type=RiskRecord&entity_id={risk_record.id}",
        headers=creator_headers,
    ).json()[0]["id"] == str(audit_log.id)
    assert client.get(
        f"/audit-logs/{audit_log.id}", headers=creator_headers
    ).status_code == 200
    assert client.get(
        f"/audit-logs?entity_type=RiskRecord&entity_id={risk_record.id}",
        headers={"X-User-Id": str(unrelated_user.id)},
    ).json() == []
    assert client.get(
        f"/audit-logs/{audit_log.id}",
        headers={"X-User-Id": str(unrelated_user.id)},
    ).status_code == 400
    assert client.get(
        f"/audit-logs/{audit_log.id}",
        headers={"X-User-Id": str(governance_reader.id)},
    ).status_code == 200
