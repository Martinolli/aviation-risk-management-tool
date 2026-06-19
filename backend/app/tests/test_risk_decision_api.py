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
from app.models.committee import Committee
from app.models.enums import (
    AuthorityLevel,
    CommitteeType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskDecision, RiskRecord


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
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


def _committee_type(authority_level: AuthorityLevel) -> CommitteeType:
    if authority_level == AuthorityLevel.LOW:
        return CommitteeType.OPERATIONAL_BOARD
    if authority_level == AuthorityLevel.MIDDLE:
        return CommitteeType.RISK_MANAGEMENT_COMMITTEE
    return CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE


def _create_committee(
    db_session: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
) -> Committee:
    committee = Committee(
        name=f"{authority_level.value} Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=_committee_type(authority_level),
        is_fixed=authority_level != AuthorityLevel.LOW,
        is_active=True,
    )
    db_session.add(committee)
    db_session.commit()
    db_session.refresh(committee)
    return committee


def _decision_payload(
    risk_record_id: uuid.UUID,
    committee_id: uuid.UUID,
    *,
    decision_type: str = "APPROVE",
    decision_text: str = "Committee decision recorded.",
) -> dict[str, object]:
    return {
        "risk_record_id": str(risk_record_id),
        "committee_id": str(committee_id),
        "decision_type": decision_type,
        "decision_text": decision_text,
    }


def _create_decision(
    db_session: Session,
    risk_record_id: uuid.UUID,
    committee_id: uuid.UUID,
) -> RiskDecision:
    decision = RiskDecision(
        risk_record_id=risk_record_id,
        committee_id=committee_id,
        decision_type=RiskDecisionType.APPROVE,
        decision_text="Committee decision recorded.",
        decided_at=datetime.now(timezone.utc),
    )
    db_session.add(decision)
    db_session.commit()
    db_session.refresh(decision)
    return decision


def test_get_risk_decisions_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    _create_decision(db_session, risk_record.id, committee.id)

    response = client.get("/risk-decisions")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_post_risk_decisions_creates_decision(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)

    response = client.post(
        "/risk-decisions",
        json=_decision_payload(risk_record.id, committee.id),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["risk_record_id"] == str(risk_record.id)
    assert body["committee_id"] == str(committee.id)
    assert body["decision_type"] == "APPROVE"


def test_post_with_empty_decision_text_returns_error(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)

    response = client.post(
        "/risk-decisions",
        json=_decision_payload(risk_record.id, committee.id, decision_text=""),
    )

    assert response.status_code in {400, 422}


def test_post_with_high_escalate_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session, authority_level=AuthorityLevel.HIGH)

    response = client.post(
        "/risk-decisions",
        json=_decision_payload(
            risk_record.id,
            committee.id,
            decision_type="ESCALATE",
        ),
    )

    assert response.status_code == 400


def test_post_with_unknown_risk_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    committee = _create_committee(db_session)

    response = client.post(
        "/risk-decisions",
        json=_decision_payload(uuid.uuid4(), committee.id),
    )

    assert response.status_code == 400


def test_post_with_unknown_committee_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.post(
        "/risk-decisions",
        json=_decision_payload(risk_record.id, uuid.uuid4()),
    )

    assert response.status_code == 400


def test_get_risk_decision_returns_decision(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    decision = _create_decision(db_session, risk_record.id, committee.id)

    response = client.get(f"/risk-decisions/{decision.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(decision.id)


def test_get_unknown_decision_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/risk-decisions/{uuid.uuid4()}")

    assert response.status_code == 404


def test_get_risk_decisions_filtered_by_risk_record_id(
    client: TestClient,
    db_session: Session,
) -> None:
    first_risk = _create_risk_record(db_session)
    second_risk = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    first_decision = _create_decision(db_session, first_risk.id, committee.id)
    _create_decision(db_session, second_risk.id, committee.id)

    response = client.get(f"/risk-decisions?risk_record_id={first_risk.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(first_decision.id)


def test_get_risk_decisions_filtered_by_committee_id(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    first_committee = _create_committee(db_session)
    second_committee = _create_committee(db_session)
    first_decision = _create_decision(db_session, risk_record.id, first_committee.id)
    _create_decision(db_session, risk_record.id, second_committee.id)

    response = client.get(f"/risk-decisions?committee_id={first_committee.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(first_decision.id)
