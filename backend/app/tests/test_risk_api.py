import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import AuditAction, RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus
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


def _risk_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "problem_description": "Unexpected vibration observed during taxi test.",
        "domain": "FLIGHT_TEST",
    }
    payload.update(overrides)
    return payload


def _create_risk_record(
    db_session: Session,
    *,
    problem_description: str = "Unexpected vibration observed during taxi test.",
) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=problem_description,
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Risk User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_get_risks_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_risk_record(db_session)

    response = client.get("/risks")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_post_risks_creates_draft_open_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    response = client.post(
        "/risks",
        json=_risk_payload(),
        headers={"X-User-Id": str(user.id)},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["problem_description"] == (
        "Unexpected vibration observed during taxi test."
    )
    assert body["workflow_status"] == "DRAFT"
    assert body["lifecycle_status"] == "OPEN"
    assert body["is_active"] is True
    assert body["created_by_user_id"] == str(user.id)


def test_post_risks_with_empty_problem_description_returns_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/risks",
        json=_risk_payload(problem_description=""),
    )

    assert response.status_code in {400, 422}


def test_post_risks_requires_active_user(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive_user = _create_user(db_session, is_active=False)

    assert client.post("/risks", json=_risk_payload()).status_code == 400
    assert client.post(
        "/risks",
        json=_risk_payload(),
        headers={"X-User-Id": str(uuid.uuid4())},
    ).status_code == 401
    assert client.post(
        "/risks",
        json=_risk_payload(),
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403


def test_get_risk_returns_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    response = client.get(f"/risks/{risk_record.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(risk_record.id)


def test_get_unknown_risk_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/risks/{uuid.uuid4()}")

    assert response.status_code == 404


def test_patch_risk_updates_allowed_field(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    response = client.patch(
        f"/risks/{risk_record.id}",
        json={"source_trigger": "Pilot report"},
        headers={"X-User-Id": str(user.id)},
    )

    assert response.status_code == 200
    assert response.json()["source_trigger"] == "Pilot report"


def test_patch_risk_with_problem_description_fails_validation(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    response = client.patch(
        f"/risks/{risk_record.id}",
        json={"problem_description": "Changed problem description"},
    )

    assert response.status_code == 422


def test_submit_risk_changes_workflow_status_to_submitted(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    response = client.post(
        f"/risks/{risk_record.id}/submit",
        json={"reason": "Ready for board review"},
        headers={"X-User-Id": str(user.id)},
    )

    assert response.status_code == 200
    assert (
        response.json()["workflow_status"]
        == "SUBMITTED_TO_OPERATIONAL_BOARD"
    )


def test_submit_risk_again_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)

    headers = {"X-User-Id": str(user.id)}
    first_response = client.post(f"/risks/{risk_record.id}/submit", json={}, headers=headers)
    second_response = client.post(f"/risks/{risk_record.id}/submit", json={}, headers=headers)

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_risk_creator_and_owner_authorize_update_and_submit(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    non_owner = _create_user(db_session)
    inactive_user = _create_user(db_session, is_active=False)
    creator_headers = {"X-User-Id": str(creator.id)}
    owner_headers = {"X-User-Id": str(owner.id)}

    creator_risk_response = client.post(
        "/risks", json=_risk_payload(), headers=creator_headers
    )
    creator_risk_id = creator_risk_response.json()["id"]
    assert creator_risk_response.status_code == 201
    assert client.patch(
        f"/risks/{creator_risk_id}", json={"source_trigger": "Updated"}
    ).status_code == 400
    assert client.patch(
        f"/risks/{creator_risk_id}",
        json={"source_trigger": "Updated"},
        headers={"X-User-Id": str(non_owner.id)},
    ).status_code == 400
    assert client.patch(
        f"/risks/{creator_risk_id}",
        json={"source_trigger": "Updated"},
        headers={"X-User-Id": str(uuid.uuid4())},
    ).status_code == 401
    assert client.patch(
        f"/risks/{creator_risk_id}",
        json={"source_trigger": "Updated"},
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403
    creator_update_response = client.patch(
        f"/risks/{creator_risk_id}",
        json={"source_trigger": "Updated"},
        headers=creator_headers,
    )
    assert creator_update_response.status_code == 200

    owner_risk_response = client.post(
        "/risks",
        json=_risk_payload(
            problem_description="Owner assigned risk.", owner_user_id=str(owner.id)
        ),
        headers=creator_headers,
    )
    owner_risk_id = owner_risk_response.json()["id"]
    assert owner_risk_response.status_code == 201
    assert client.post(f"/risks/{owner_risk_id}/submit", json={}).status_code == 400
    assert client.post(
        f"/risks/{owner_risk_id}/submit",
        json={},
        headers=creator_headers,
    ).status_code == 400
    assert client.post(
        f"/risks/{owner_risk_id}/submit",
        json={},
        headers={"X-User-Id": str(uuid.uuid4())},
    ).status_code == 401
    assert client.post(
        f"/risks/{owner_risk_id}/submit",
        json={},
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403
    submit_response = client.post(
        f"/risks/{owner_risk_id}/submit",
        json={"reason": "Owner submission"},
        headers=owner_headers,
    )
    update_audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(creator_risk_id),
            AuditLog.action == AuditAction.UPDATE,
        )
    )
    submit_audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(owner_risk_id),
            AuditLog.action == AuditAction.SUBMIT,
        )
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["workflow_status"] == "SUBMITTED_TO_OPERATIONAL_BOARD"
    assert update_audit_log is not None
    assert update_audit_log.changed_by_user_id == creator.id
    assert submit_audit_log is not None
    assert submit_audit_log.changed_by_user_id == owner.id
