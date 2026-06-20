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
from app.models.committee import Committee
from app.models.enums import AuditAction, AuthorityLevel, CommitteeType
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


def _risk_payload() -> dict[str, str]:
    return {
        "problem_description": "Unexpected vibration observed during taxi test.",
        "domain": "FLIGHT_TEST",
    }


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Attribution User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_committee(db_session: Session) -> Committee:
    committee = Committee(
        name=f"Attribution Committee {uuid.uuid4()}",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_active=True,
    )
    db_session.add(committee)
    db_session.commit()
    db_session.refresh(committee)
    return committee


def _audit_log(
    db_session: Session,
    *,
    entity_id: uuid.UUID,
    action: AuditAction,
    field_name: str | None = None,
) -> AuditLog:
    statement = select(AuditLog).where(
        AuditLog.entity_id == entity_id,
        AuditLog.action == action,
    )
    if field_name is not None:
        statement = statement.where(AuditLog.field_name == field_name)
    audit_log = db_session.scalar(statement.order_by(AuditLog.changed_at.desc()))
    assert audit_log is not None
    return audit_log


def test_write_without_header_preserves_anonymous_behavior(client: TestClient) -> None:
    response = client.post("/risks", json=_risk_payload())

    assert response.status_code == 201
    assert response.json()["created_by_user_id"] is None


def test_valid_header_attributes_workflow_operations(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    user = _create_user(db_session)
    headers = {"X-User-Id": str(user.id)}

    risk_response = client.post("/risks", json=_risk_payload(), headers=headers)
    risk_id = uuid.UUID(risk_response.json()["id"])
    assert risk_response.status_code == 201
    assert risk_response.json()["created_by_user_id"] == str(user.id)
    assert db_session.get(RiskRecord, risk_id).created_by_user_id == user.id
    assert _audit_log(
        db_session, entity_id=risk_id, action=AuditAction.CREATE
    ).changed_by_user_id == user.id

    submit_response = client.post(
        f"/risks/{risk_id}/submit",
        json={"reason": "Ready for review"},
        headers=headers,
    )
    assert submit_response.status_code == 200
    assert _audit_log(
        db_session, entity_id=risk_id, action=AuditAction.SUBMIT
    ).changed_by_user_id == user.id

    assessment_response = client.post(
        "/risk-assessments",
        json={
            "risk_record_id": str(risk_id),
            "assessment_type": "INITIAL",
            "severity": "Major",
            "likelihood": "Remote",
            "risk_level": "Medium",
        },
        headers=headers,
    )
    assert assessment_response.status_code == 201
    assert assessment_response.json()["assessed_by_user_id"] == str(user.id)

    action_response = client.post(
        "/risk-actions",
        json={"risk_record_id": str(risk_id), "title": "Inspect instrumentation"},
        headers=headers,
    )
    action_id = uuid.UUID(action_response.json()["id"])
    assert action_response.status_code == 201
    assert _audit_log(
        db_session, entity_id=action_id, action=AuditAction.CREATE
    ).changed_by_user_id == user.id

    complete_response = client.post(
        f"/risk-actions/{action_id}/complete",
        json={"completion_notes": "Complete"},
        headers=headers,
    )
    assert complete_response.status_code == 200
    assert _audit_log(
        db_session,
        entity_id=action_id,
        action=AuditAction.UPDATE,
        field_name="status",
    ).changed_by_user_id == user.id

    committee = _create_committee(db_session)
    decision_response = client.post(
        "/risk-decisions",
        json={
            "risk_record_id": str(risk_id),
            "committee_id": str(committee.id),
            "decision_type": "APPROVE",
            "decision_text": "Approved for action.",
        },
        headers=headers,
    )
    assert decision_response.status_code == 201
    assert decision_response.json()["decided_by_user_id"] == str(user.id)

    report_response = client.post(
        f"/reports/risk-dossiers/{risk_id}",
        json={"output_dir": str(tmp_path)},
        headers=headers,
    )
    assert report_response.status_code == 201
    assert report_response.json()["generated_by_user_id"] == str(user.id)


def test_unknown_and_inactive_header_users_are_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    unknown_response = client.post(
        "/risks",
        json=_risk_payload(),
        headers={"X-User-Id": str(uuid.uuid4())},
    )
    inactive_user = _create_user(db_session, is_active=False)
    inactive_response = client.post(
        "/risks",
        json=_risk_payload(),
        headers={"X-User-Id": str(inactive_user.id)},
    )

    assert unknown_response.status_code == 401
    assert unknown_response.json()["detail"] == "User not found"
    assert inactive_response.status_code == 403
    assert inactive_response.json()["detail"] == "User is inactive"
