import uuid
from collections.abc import Generator
from datetime import datetime, timezone

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
    RiskAssessmentType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAssessment, RiskRecord


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


def _assessment_payload(
    risk_record_id: uuid.UUID,
    *,
    assessment_type: str = "INITIAL",
) -> dict[str, object]:
    return {
        "risk_record_id": str(risk_record_id),
        "assessment_type": assessment_type,
        "severity": "Major",
        "likelihood": "Remote",
        "risk_level": "Medium",
        "rationale": "Initial rationale",
    }


def _create_assessment(
    db_session: Session,
    risk_record_id: uuid.UUID,
    *,
    assessment_type: RiskAssessmentType = RiskAssessmentType.INITIAL,
) -> RiskAssessment:
    assessment = RiskAssessment(
        risk_record_id=risk_record_id,
        assessment_type=assessment_type,
        severity="Major",
        likelihood="Remote",
        risk_level="Medium",
        rationale="Initial rationale",
        assessed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)
    return assessment


def test_get_risk_assessments_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    _create_assessment(db_session, risk_record.id)

    response = client.get("/risk-assessments")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_post_risk_assessments_creates_assessment(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.post(
        "/risk-assessments",
        json=_assessment_payload(risk_record.id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["risk_record_id"] == str(risk_record.id)
    assert body["assessment_type"] == "INITIAL"
    assert body["severity"] == "Major"


def test_post_duplicate_initial_assessment_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    _create_assessment(db_session, risk_record.id)

    response = client.post(
        "/risk-assessments",
        json=_assessment_payload(risk_record.id),
    )

    assert response.status_code == 400


def test_get_risk_assessment_returns_assessment(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    assessment = _create_assessment(db_session, risk_record.id)

    response = client.get(f"/risk-assessments/{assessment.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(assessment.id)


def test_get_unknown_assessment_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/risk-assessments/{uuid.uuid4()}")

    assert response.status_code == 404


def test_patch_risk_assessment_updates_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    assessment = _create_assessment(db_session, risk_record.id)

    response = client.patch(
        f"/risk-assessments/{assessment.id}",
        json={
            "severity": "Hazardous",
            "likelihood": "Occasional",
            "risk_level": "High",
            "rationale": "Updated rationale",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "Hazardous"
    assert body["likelihood"] == "Occasional"
    assert body["risk_level"] == "High"
    assert body["rationale"] == "Updated rationale"


def test_patch_unknown_assessment_returns_http_404(client: TestClient) -> None:
    response = client.patch(
        f"/risk-assessments/{uuid.uuid4()}",
        json={"severity": "Hazardous"},
    )

    assert response.status_code == 404


def test_get_risk_assessments_filtered_by_risk_record_id(
    client: TestClient,
    db_session: Session,
) -> None:
    first_risk = _create_risk_record(db_session)
    second_risk = _create_risk_record(db_session)
    first_assessment = _create_assessment(db_session, first_risk.id)
    _create_assessment(db_session, second_risk.id)

    response = client.get(f"/risk-assessments?risk_record_id={first_risk.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(first_assessment.id)
