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
from app.models.enums import RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus
from app.models.risk import RiskRecord


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


def test_get_risks_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_risk_record(db_session)

    response = client.get("/risks")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_post_risks_creates_draft_open_risk(client: TestClient) -> None:
    response = client.post("/risks", json=_risk_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["problem_description"] == (
        "Unexpected vibration observed during taxi test."
    )
    assert body["workflow_status"] == "DRAFT"
    assert body["lifecycle_status"] == "OPEN"
    assert body["is_active"] is True


def test_post_risks_with_empty_problem_description_returns_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/risks",
        json=_risk_payload(problem_description=""),
    )

    assert response.status_code in {400, 422}


def test_get_risk_returns_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

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

    response = client.patch(
        f"/risks/{risk_record.id}",
        json={"source_trigger": "Pilot report"},
    )

    assert response.status_code == 200
    assert response.json()["source_trigger"] == "Pilot report"


def test_patch_risk_with_problem_description_fails_validation(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

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

    response = client.post(
        f"/risks/{risk_record.id}/submit",
        json={"reason": "Ready for board review"},
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

    first_response = client.post(f"/risks/{risk_record.id}/submit", json={})
    second_response = client.post(f"/risks/{risk_record.id}/submit", json={})

    assert first_response.status_code == 200
    assert second_response.status_code == 400
