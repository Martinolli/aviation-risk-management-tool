import uuid
from collections.abc import Generator
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.enums import (
    RiskActionStatus,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskRecord


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


def _create_risk_record(db_session: Session) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


def _action_payload(
    risk_record_id: uuid.UUID,
    *,
    title: str = "Inspect flight test instrumentation",
) -> dict[str, object]:
    return {
        "risk_record_id": str(risk_record_id),
        "title": title,
        "description": "Mitigation action",
        "due_date": "2026-06-30",
    }


def _create_action(db_session: Session, risk_record_id: uuid.UUID) -> RiskAction:
    action = RiskAction(
        risk_record_id=risk_record_id,
        title="Inspect flight test instrumentation",
        description="Mitigation action",
        due_date=date(2026, 6, 30),
        status=RiskActionStatus.OPEN,
    )
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)
    return action


def test_get_risk_actions_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    _create_action(db_session, risk_record.id)

    response = client.get("/risk-actions")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_post_risk_actions_creates_action(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.post("/risk-actions", json=_action_payload(risk_record.id))

    assert response.status_code == 201
    body = response.json()
    assert body["risk_record_id"] == str(risk_record.id)
    assert body["title"] == "Inspect flight test instrumentation"
    assert body["status"] == "OPEN"


def test_post_risk_actions_with_empty_title_returns_error(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.post(
        "/risk-actions",
        json=_action_payload(risk_record.id, title=""),
    )

    assert response.status_code in {400, 422}


def test_post_risk_actions_for_unknown_risk_returns_http_400(
    client: TestClient,
) -> None:
    response = client.post("/risk-actions", json=_action_payload(uuid.uuid4()))

    assert response.status_code == 400


def test_get_risk_action_returns_action(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)

    response = client.get(f"/risk-actions/{action.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(action.id)


def test_get_unknown_action_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/risk-actions/{uuid.uuid4()}")

    assert response.status_code == 404


def test_patch_risk_action_updates_valid_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)

    response = client.patch(
        f"/risk-actions/{action.id}",
        json={
            "title": "Revise inspection plan",
            "description": "Updated mitigation",
            "due_date": "2026-07-15",
            "status": "IN_PROGRESS",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Revise inspection plan"
    assert body["description"] == "Updated mitigation"
    assert body["due_date"] == "2026-07-15"
    assert body["status"] == "IN_PROGRESS"


def test_patch_risk_action_with_status_completed_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)

    response = client.patch(
        f"/risk-actions/{action.id}",
        json={"status": "COMPLETED"},
    )

    assert response.status_code == 400


def test_complete_risk_action_completes_action(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)

    response = client.post(
        f"/risk-actions/{action.id}/complete",
        json={"completion_notes": "Inspection completed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["completion_notes"] == "Inspection completed"
    assert body["completed_at"] is not None


def test_complete_risk_action_again_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)
    action.status = RiskActionStatus.COMPLETED
    action.completed_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.post(
        f"/risk-actions/{action.id}/complete",
        json={"completion_notes": "Already done"},
    )

    assert response.status_code == 400


def test_get_risk_actions_filtered_by_risk_record_id(
    client: TestClient,
    db_session: Session,
) -> None:
    first_risk = _create_risk_record(db_session)
    second_risk = _create_risk_record(db_session)
    first_action = _create_action(db_session, first_risk.id)
    _create_action(db_session, second_risk.id)

    response = client.get(f"/risk-actions?risk_record_id={first_risk.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(first_action.id)
