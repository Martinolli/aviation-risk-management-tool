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
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, CommitteeType
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


def _admin_headers(db_session: Session) -> dict[str, str]:
    user = User(email="smoke-admin@example.com", display_name="Smoke Admin", is_active=True)
    committee = Committee(
        name="Smoke Governance Committee",
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        is_fixed=True,
        is_active=True,
    )
    db_session.add_all([user, committee])
    db_session.flush()
    db_session.add(CommitteeMember(committee_id=committee.id, user_id=user.id, is_active=True))
    db_session.commit()
    return {"X-User-Id": str(user.id)}


def _create_committee(client: TestClient, admin_headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/committees",
        json={
            "name": "Flight Test Safety Committee - Smoke",
            "description": "Operational board for smoke tests.",
            "authority_level": "LOW",
            "committee_type": "OPERATIONAL_BOARD",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_risk(
    client: TestClient,
    committee_id: str | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "problem_description": "Unexpected vibration observed during taxi test.",
        "domain": "FLIGHT_TEST",
        "source_trigger": "Pilot report",
        "system_scope": "Flight test aircraft",
        "central_event": "Vibration during ground movement",
        "hazard_statement": "Loss of component integrity could affect safety margin.",
        "causes": ["Loose instrumentation mount", "Unverified installation torque"],
        "consequences": ["Equipment damage", "Test abort"],
        "existing_controls": ["Pre-flight inspection", "Engineering review"],
    }
    if committee_id is not None:
        payload["board_of_origin_id"] = committee_id

    response = client.post("/risks", json=payload, headers=headers)
    assert response.status_code == 201
    return response.json()


def _create_risk_actor_headers(
    client: TestClient, admin_headers: dict[str, str]
) -> dict[str, str]:
    response = client.post(
        "/users",
        json={
            "email": "smoke-risk-actor@example.com",
            "display_name": "Smoke Risk Actor",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    return {"X-User-Id": response.json()["id"]}


def _create_assessment(
    client: TestClient,
    risk_record_id: str,
    assessment_type: str,
    headers: dict[str, str],
) -> dict[str, object]:
    response = client.post(
        "/risk-assessments",
        json={
            "risk_record_id": risk_record_id,
            "assessment_type": assessment_type,
            "severity": "Major",
            "likelihood": "Remote",
            "risk_level": "Medium",
            "rationale": f"{assessment_type} assessment for smoke workflow.",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def _create_action(client: TestClient, risk_record_id: str) -> dict[str, object]:
    response = client.post(
        "/risk-actions",
        json={
            "risk_record_id": risk_record_id,
            "title": "Inspect instrumentation mount",
            "description": "Verify mount installation and torque.",
            "due_date": "2026-06-30",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_action_actor_headers(
    client: TestClient,
    risk_record_id: str,
    admin_headers: dict[str, str],
) -> dict[str, str]:
    response = client.post(
        "/users",
        json={
            "email": f"action-{risk_record_id}@example.com",
            "display_name": "Smoke Action Actor",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    return {"X-User-Id": response.json()["id"]}


def _create_assessment_actor_headers(
    client: TestClient,
    risk_record_id: str,
    admin_headers: dict[str, str],
) -> dict[str, str]:
    response = client.post(
        "/users",
        json={
            "email": f"assessment-{risk_record_id}@example.com",
            "display_name": "Smoke Assessment Actor",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    return {"X-User-Id": response.json()["id"]}


def _create_decision_headers(
    client: TestClient,
    committee_id: str,
    admin_headers: dict[str, str],
) -> dict[str, str]:
    user_response = client.post(
        "/users",
        json={
            "email": f"decision-{committee_id}@example.com",
            "display_name": "Smoke Decision Maker",
        },
        headers=admin_headers,
    )
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]
    membership_response = client.post(
        "/committee-members",
        json={"committee_id": committee_id, "user_id": user_id},
        headers=admin_headers,
    )
    assert membership_response.status_code == 201
    return {"X-User-Id": user_id}


def _create_decision(
    client: TestClient,
    risk_record_id: str,
    committee_id: str,
    decision_type: str,
    headers: dict[str, str],
) -> dict[str, object]:
    response = client.post(
        "/risk-decisions",
        json={
            "risk_record_id": risk_record_id,
            "committee_id": committee_id,
            "decision_type": decision_type,
            "decision_text": f"{decision_type} decision recorded by committee.",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def test_full_risk_workflow_through_api(client: TestClient, db_session: Session) -> None:
    admin_headers = _admin_headers(db_session)
    committee = _create_committee(client, admin_headers)
    committee_id = committee["id"]
    decision_headers = _create_decision_headers(client, committee_id, admin_headers)
    risk_headers = _create_risk_actor_headers(client, admin_headers)

    risk = _create_risk(client, committee_id=committee_id, headers=risk_headers)
    risk_record_id = risk["id"]

    assert risk["risk_id"] is not None
    assert risk["workflow_status"] == "DRAFT"
    assert risk["lifecycle_status"] == "OPEN"

    submit_response = client.post(
        f"/risks/{risk_record_id}/submit",
        json={"reason": "Ready for operational board review"},
        headers=risk_headers,
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["workflow_status"] == (
        "SUBMITTED_TO_OPERATIONAL_BOARD"
    )

    assessment_headers = _create_assessment_actor_headers(client, risk_record_id, admin_headers)
    initial_assessment = _create_assessment(
        client,
        risk_record_id,
        "INITIAL",
        assessment_headers,
    )
    action = _create_action(client, risk_record_id)
    action_headers = _create_action_actor_headers(client, risk_record_id, admin_headers)

    complete_response = client.post(
        f"/risk-actions/{action['id']}/complete",
        json={"completion_notes": "Mount inspected and secured."},
        headers=action_headers,
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "COMPLETED"

    residual_assessment = _create_assessment(
        client,
        risk_record_id,
        "RESIDUAL",
        assessment_headers,
    )
    decision = _create_decision(
        client,
        risk_record_id,
        committee_id,
        "APPROVE",
        decision_headers,
    )
    assert decision["decision_type"] == "APPROVE"

    risk_response = client.get(f"/risks/{risk_record_id}")
    assert risk_response.status_code == 200
    assert risk_response.json()["workflow_status"] == (
        "APPROVED_AT_OPERATIONAL_BOARD"
    )

    detail_response = client.get(f"/risks/{risk_record_id}/detail", headers=risk_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()

    assert detail["risk_record"]["id"] == risk_record_id
    assert {item["assessment_type"] for item in detail["assessments"]} == {
        "INITIAL",
        "RESIDUAL",
    }
    assert {item["id"] for item in detail["assessments"]} == {
        initial_assessment["id"],
        residual_assessment["id"],
    }
    assert len(detail["actions"]) == 1
    assert detail["actions"][0]["status"] == "COMPLETED"
    assert len(detail["decisions"]) == 1
    assert detail["decisions"][0]["id"] == decision["id"]
    assert detail["audit_summary"]["total_count"] >= 2
    assert detail["audit_summary"]["workflow_count"] >= 2

    audit_response = client.get(
        f"/audit-logs?entity_type=RiskRecord&entity_id={risk_record_id}",
        headers=risk_headers,
    )
    assert audit_response.status_code == 200
    audit_actions = {item["action"] for item in audit_response.json()}
    assert {"CREATE", "SUBMIT", "APPROVE"}.issubset(audit_actions)


def test_invalid_governance_decisions_through_api(client: TestClient, db_session: Session) -> None:
    admin_headers = _admin_headers(db_session)
    committee = _create_committee(client, admin_headers)
    decision_headers = _create_decision_headers(client, committee["id"], admin_headers)
    risk = _create_risk(
        client,
        committee_id=committee["id"],
        headers=_create_risk_actor_headers(client, admin_headers),
    )

    approve_decision = _create_decision(
        client,
        risk["id"],
        committee["id"],
        "APPROVE",
        decision_headers,
    )
    assert approve_decision["decision_type"] == "APPROVE"

    close_response = client.post(
        "/risk-decisions",
        json={
            "risk_record_id": risk["id"],
            "committee_id": committee["id"],
            "decision_type": "CLOSE",
            "decision_text": "Attempting LOW close.",
        },
        headers=decision_headers,
    )
    assert close_response.status_code == 400

    accept_residual_response = client.post(
        "/risk-decisions",
        json={
            "risk_record_id": risk["id"],
            "committee_id": committee["id"],
            "decision_type": "ACCEPT_RESIDUAL_RISK",
            "decision_text": "Attempting LOW residual risk acceptance.",
        },
        headers=decision_headers,
    )
    assert accept_residual_response.status_code == 400


def test_completed_action_protection_through_api(client: TestClient, db_session: Session) -> None:
    admin_headers = _admin_headers(db_session)
    risk = _create_risk(client, headers=_create_risk_actor_headers(client, admin_headers))
    action = _create_action(client, risk["id"])
    action_headers = _create_action_actor_headers(client, risk["id"], admin_headers)

    complete_response = client.post(
        f"/risk-actions/{action['id']}/complete",
        json={"completion_notes": "Completed mitigation action."},
        headers=action_headers,
    )
    assert complete_response.status_code == 200

    patch_response = client.patch(
        f"/risk-actions/{action['id']}",
        json={"title": "Changed after completion"},
        headers=action_headers,
    )
    assert patch_response.status_code == 400
