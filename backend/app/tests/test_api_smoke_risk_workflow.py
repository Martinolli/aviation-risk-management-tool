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


def _create_committee(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/committees",
        json={
            "name": "Flight Test Safety Committee - Smoke",
            "description": "Operational board for smoke tests.",
            "authority_level": "LOW",
            "committee_type": "OPERATIONAL_BOARD",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_risk(
    client: TestClient,
    committee_id: str | None = None,
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

    response = client.post("/risks", json=payload)
    assert response.status_code == 201
    return response.json()


def _create_assessment(
    client: TestClient,
    risk_record_id: str,
    assessment_type: str,
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


def _create_decision(
    client: TestClient,
    risk_record_id: str,
    committee_id: str,
    decision_type: str,
) -> dict[str, object]:
    response = client.post(
        "/risk-decisions",
        json={
            "risk_record_id": risk_record_id,
            "committee_id": committee_id,
            "decision_type": decision_type,
            "decision_text": f"{decision_type} decision recorded by committee.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_full_risk_workflow_through_api(client: TestClient) -> None:
    committee = _create_committee(client)
    committee_id = committee["id"]

    risk = _create_risk(client, committee_id=committee_id)
    risk_record_id = risk["id"]

    assert risk["risk_id"] is not None
    assert risk["workflow_status"] == "DRAFT"
    assert risk["lifecycle_status"] == "OPEN"

    submit_response = client.post(
        f"/risks/{risk_record_id}/submit",
        json={"reason": "Ready for operational board review"},
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["workflow_status"] == (
        "SUBMITTED_TO_OPERATIONAL_BOARD"
    )

    initial_assessment = _create_assessment(client, risk_record_id, "INITIAL")
    action = _create_action(client, risk_record_id)

    complete_response = client.post(
        f"/risk-actions/{action['id']}/complete",
        json={"completion_notes": "Mount inspected and secured."},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "COMPLETED"

    residual_assessment = _create_assessment(client, risk_record_id, "RESIDUAL")
    decision = _create_decision(client, risk_record_id, committee_id, "APPROVE")
    assert decision["decision_type"] == "APPROVE"

    risk_response = client.get(f"/risks/{risk_record_id}")
    assert risk_response.status_code == 200
    assert risk_response.json()["workflow_status"] == (
        "APPROVED_AT_OPERATIONAL_BOARD"
    )

    detail_response = client.get(f"/risks/{risk_record_id}/detail")
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
        f"/audit-logs?entity_type=RiskRecord&entity_id={risk_record_id}"
    )
    assert audit_response.status_code == 200
    audit_actions = {item["action"] for item in audit_response.json()}
    assert {"CREATE", "SUBMIT", "APPROVE"}.issubset(audit_actions)


def test_invalid_governance_decisions_through_api(client: TestClient) -> None:
    committee = _create_committee(client)
    risk = _create_risk(client, committee_id=committee["id"])

    approve_decision = _create_decision(
        client,
        risk["id"],
        committee["id"],
        "APPROVE",
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
    )
    assert accept_residual_response.status_code == 400


def test_completed_action_protection_through_api(client: TestClient) -> None:
    risk = _create_risk(client)
    action = _create_action(client, risk["id"])

    complete_response = client.post(
        f"/risk-actions/{action['id']}/complete",
        json={"completion_notes": "Completed mitigation action."},
    )
    assert complete_response.status_code == 200

    patch_response = client.patch(
        f"/risk-actions/{action['id']}",
        json={"title": "Changed after completion"},
    )
    assert patch_response.status_code == 400
