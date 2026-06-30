import uuid
from datetime import timedelta
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuditAction, AuthorityLevel, CommitteeType
from app.models.risk import RiskRecord
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


def _create_membership(
    db_session: Session,
    *,
    committee: Committee,
    user: User,
) -> CommitteeMember:
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        is_active=True,
    )
    db_session.add(membership)
    db_session.commit()
    db_session.refresh(membership)
    return membership


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


def test_risk_write_without_header_is_rejected(client: TestClient) -> None:
    response = client.post("/risks", json=_risk_payload())

    assert response.status_code == 400


def test_valid_header_attributes_workflow_operations(
    client: TestClient,
    db_session: Session,
    tmp_path,
) -> None:
    user = _create_user(db_session)
    committee = _create_committee(db_session)
    _create_membership(db_session, committee=committee, user=user)
    headers = {"X-User-Id": str(user.id)}

    risk_response = client.post(
        "/risks",
        json={
            **_risk_payload(),
            "board_of_origin_id": str(committee.id),
            "system_scope": "Flight test aircraft",
            "central_event": "Unexpected vibration during taxi",
            "hazard_statement": "Vibration may cause loss of component integrity",
        },
        headers=headers,
    )
    risk_id = uuid.UUID(risk_response.json()["id"])
    assert risk_response.status_code == 201
    assert risk_response.json()["created_by_user_id"] == str(user.id)
    assert db_session.get(RiskRecord, risk_id).created_by_user_id == user.id
    assert _audit_log(
        db_session, entity_id=risk_id, action=AuditAction.CREATE
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

    submit_response = client.post(
        f"/risks/{risk_id}/submit",
        json={"reason": "Ready for review"},
        headers=headers,
    )
    assert submit_response.status_code == 200
    assert _audit_log(
        db_session, entity_id=risk_id, action=AuditAction.SUBMIT
    ).changed_by_user_id == user.id

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
    assert unknown_response.json()["error"]["message"] == "User not found"
    assert inactive_response.status_code == 403
    assert inactive_response.json()["error"]["message"] == "User is inactive"


def test_bearer_token_authenticates_and_takes_precedence_over_x_user_id(
    client: TestClient,
    db_session: Session,
) -> None:
    token_user = _create_user(db_session)
    conflicting_user = _create_user(db_session, is_active=False)
    token = create_access_token(user_id=token_user.id)

    response = client.post(
        "/risks",
        json=_risk_payload(),
        headers={
            "Authorization": f"Bearer {token}",
            "X-User-Id": str(conflicting_user.id),
        },
    )

    assert response.status_code == 201
    assert response.json()["created_by_user_id"] == str(token_user.id)


@pytest.mark.parametrize(
    "authorization,expected_detail",
    [
        ("not-a-token", "Invalid authorization header"),
        ("Basic abc", "Invalid authorization header"),
        ("Bearer malformed", "Invalid or expired access token"),
    ],
)
def test_invalid_authorization_headers_are_rejected(
    client: TestClient,
    authorization: str,
    expected_detail: str,
) -> None:
    response = client.post(
        "/risks",
        json=_risk_payload(),
        headers={"Authorization": authorization},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
    assert response.json()["error"]["message"] == expected_detail


def test_expired_unknown_and_inactive_bearer_users_are_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive_user = _create_user(db_session, is_active=False)
    expired_token = create_access_token(
        user_id=uuid.uuid4(), expires_delta=timedelta(seconds=-1)
    )
    unknown_token = create_access_token(user_id=uuid.uuid4())
    inactive_token = create_access_token(user_id=inactive_user.id)

    expired_response = client.post(
        "/risks", json=_risk_payload(), headers={"Authorization": f"Bearer {expired_token}"}
    )
    unknown_response = client.post(
        "/risks", json=_risk_payload(), headers={"Authorization": f"Bearer {unknown_token}"}
    )
    inactive_response = client.post(
        "/risks", json=_risk_payload(), headers={"Authorization": f"Bearer {inactive_token}"}
    )

    assert expired_response.status_code == 401
    assert unknown_response.status_code == 401
    assert inactive_response.status_code == 403


def test_bearer_authentication_works_when_x_user_id_fallback_is_disabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db_session)
    monkeypatch.setattr(settings, "enable_x_user_id_auth_fallback", False)

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {create_access_token(user_id=user.id)}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_x_user_id_fallback_works_when_explicitly_enabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db_session)
    monkeypatch.setattr(settings, "enable_x_user_id_auth_fallback", True)

    response = client.get("/auth/me", headers={"X-User-Id": str(user.id)})

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_x_user_id_fallback_is_rejected_when_disabled(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db_session)
    monkeypatch.setattr(settings, "enable_x_user_id_auth_fallback", False)

    response = client.get("/auth/me", headers={"X-User-Id": str(user.id)})

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "UNAUTHENTICATED",
            "message": "X-User-Id authentication fallback is disabled",
            "details": {},
        }
    }


def test_invalid_bearer_token_is_not_bypassed_by_x_user_id_fallback(
    client: TestClient,
    db_session: Session,
) -> None:
    fallback_user = _create_user(db_session)

    response = client.post(
        "/risks",
        json=_risk_payload(),
        headers={
            "Authorization": "Bearer invalid",
            "X-User-Id": str(fallback_user.id),
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
