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
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee
from app.models.enums import (
    AuditAction,
    AuthorityLevel,
    CommitteeType,
    RiskActionStatus,
    RiskAssessmentType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord


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
        risk_id=f"RISK-2026-{uuid.uuid4().int % 9999:04d}",
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


def _create_committee(db_session: Session) -> Committee:
    committee = Committee(
        name=f"Committee {uuid.uuid4()}",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=False,
        is_active=True,
    )
    db_session.add(committee)
    db_session.commit()
    db_session.refresh(committee)
    return committee


def _seed_detail_data(db_session: Session, risk_record: RiskRecord) -> None:
    now = datetime.now(timezone.utc)
    committee = _create_committee(db_session)
    db_session.add_all(
        [
            RiskAssessment(
                risk_record_id=risk_record.id,
                assessment_type=RiskAssessmentType.INITIAL,
                severity="Major",
                likelihood="Remote",
                risk_level="Medium",
                assessed_at=now,
            ),
            RiskAction(
                risk_record_id=risk_record.id,
                title="Mitigation action",
                status=RiskActionStatus.OPEN,
            ),
            RiskDecision(
                risk_record_id=risk_record.id,
                committee_id=committee.id,
                decision_type=RiskDecisionType.APPROVE,
                decision_text="Approved.",
                decided_at=now,
            ),
            AuditLog(
                entity_type="RiskRecord",
                entity_id=risk_record.id,
                action=AuditAction.CREATE,
                changed_at=now,
            ),
        ]
    )
    db_session.commit()


def test_get_risk_detail_returns_200(client: TestClient, db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.get(f"/risks/{risk_record.id}/detail")

    assert response.status_code == 200


def test_get_risk_detail_response_includes_aggregate_sections(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    _seed_detail_data(db_session, risk_record)

    response = client.get(f"/risks/{risk_record.id}/detail")

    assert response.status_code == 200
    body = response.json()
    assert body["risk_record"]["id"] == str(risk_record.id)
    assert isinstance(body["assessments"], list)
    assert isinstance(body["actions"], list)
    assert isinstance(body["decisions"], list)
    assert body["audit_summary"]["total_count"] == 1


def test_get_unknown_risk_detail_returns_404(client: TestClient) -> None:
    response = client.get(f"/risks/{uuid.uuid4()}/detail")

    assert response.status_code == 404


def test_get_risk_record_still_works_with_detail_route(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.get(f"/risks/{risk_record.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(risk_record.id)
