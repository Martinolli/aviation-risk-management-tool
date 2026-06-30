from collections.abc import Generator
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.risk_matrix import RiskLevel, RiskLikelihoodLevel, RiskSeverityLevel
from app.services.bootstrap_service import bootstrap_governance_admin
from app.services.default_risk_matrix_seed_service import seed_default_risk_matrix


def _create_test_client() -> tuple[TestClient, Session, object]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), session, engine


def _login(client: TestClient) -> tuple[dict[str, str], dict[str, object]]:
    response = client.post("/auth/login", json={"email": "admin@example.com", "password": "StrongPassword123!"})
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]


def _matrix_level(db: Session, model, code: str):
    level = db.scalar(select(model).where(model.code == code))
    assert level is not None
    return level


def test_end_to_end_bootstrap_seed_login_risk_assessment_decision_report_workflow(tmp_path) -> None:
    client, db, engine = _create_test_client()
    try:
        bootstrap_governance_admin(db, admin_email="admin@example.com", admin_display_name="Admin User", admin_password="StrongPassword123!")
        seed_default_risk_matrix(db)
        db.commit()

        headers, user = _login(client)
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "admin@example.com"
        assert "password" not in me_response.json()
        assert "password_hash" not in me_response.json()

        flight_test_committee = db.scalar(
            select(Committee).where(
                Committee.name == "Flight Test Safety Committee - Operation"
            )
        )
        assert flight_test_committee is not None
        db.add(
            CommitteeMember(
                committee_id=flight_test_committee.id,
                user_id=uuid.UUID(str(user["id"])),
                role_label="Test Operational Board Member",
                is_active=True,
            )
        )
        db.commit()

        risk_response = client.post("/risks", json={
            "problem_description": "Landing gear indication instability observed after maintenance.",
            "domain": "FLIGHT_TEST",
            "board_of_origin_id": str(flight_test_committee.id),
            "source_trigger": "Flight test preparation observation",
            "system_scope": "Landing gear indication system",
            "central_event": "Unstable landing gear indication",
            "hazard_statement": "Unreliable indication may reduce crew status awareness.",
            "causes": ["Wiring disturbance", "Sensor misalignment"],
            "consequences": ["Incorrect landing gear status awareness"],
            "existing_controls": ["Maintenance inspection", "Functional test"],
        }, headers=headers)
        assert risk_response.status_code == 201
        risk = risk_response.json()
        assert risk["risk_id"].startswith("RISK-")
        assert risk["created_by_user_id"] == user["id"]
        assert risk["workflow_status"] == "DRAFT"

        severity_s3 = _matrix_level(db, RiskSeverityLevel, "S3")
        likelihood_l3 = _matrix_level(db, RiskLikelihoodLevel, "L3")
        severity_s2 = _matrix_level(db, RiskSeverityLevel, "S2")
        likelihood_l2 = _matrix_level(db, RiskLikelihoodLevel, "L2")
        high_level = _matrix_level(db, RiskLevel, "HIGH")
        initial_response = client.post("/risk-assessments", json={
            "risk_record_id": risk["id"], "assessment_type": "INITIAL",
            "severity_level_id": str(severity_s3.id), "likelihood_level_id": str(likelihood_l3.id),
            "rationale": "Repeated instability significantly reduces safety margin.",
        }, headers=headers)
        assert initial_response.status_code == 201
        initial = initial_response.json()
        assert initial["severity_level_id"] == str(severity_s3.id)
        assert initial["likelihood_level_id"] == str(likelihood_l3.id)
        assert initial["calculated_score"] == 9
        assert initial["risk_level"] == "HIGH"
        assert initial["calculated_risk_level_id"] == str(high_level.id)
        assert initial["is_tolerable"] is False
        assert initial["requires_mitigation"] is True
        assert initial["requires_escalation"] is True

        submit_response = client.post(f"/risks/{risk['id']}/submit", json={"reason": "Ready for operational board review"}, headers=headers)
        assert submit_response.status_code == 200
        assert submit_response.json()["workflow_status"] == "SUBMITTED_TO_OPERATIONAL_BOARD"

        action_response = client.post("/risk-actions", json={
            "risk_record_id": risk["id"], "title": "Perform landing gear indication troubleshooting",
            "description": "Inspect wiring, connectors, sensor alignment, and repeat functional tests.",
            "action_owner_user_id": user["id"],
        }, headers=headers)
        assert action_response.status_code == 201
        action = action_response.json()
        assert action["status"] == "OPEN"
        assert action["action_owner_user_id"] == user["id"]
        complete_response = client.post(f"/risk-actions/{action['id']}/complete", json={"completion_notes": "Stable indication confirmed during repeated functional test."}, headers=headers)
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "COMPLETED"
        assert complete_response.json()["completed_at"] is not None

        residual_response = client.post("/risk-assessments", json={
            "risk_record_id": risk["id"], "assessment_type": "RESIDUAL",
            "severity_level_id": str(severity_s2.id), "likelihood_level_id": str(likelihood_l2.id),
            "rationale": "Mitigations reduce residual risk to a tolerable level.",
        }, headers=headers)
        assert residual_response.status_code == 201
        residual = residual_response.json()
        assert residual["calculated_score"] == 4
        assert residual["risk_level"] == "MEDIUM"
        assert residual["is_tolerable"] is True
        assert residual["requires_mitigation"] is True
        assert residual["requires_escalation"] is False

        escalation_response = client.post("/risk-decisions", json={
            "risk_record_id": risk["id"], "committee_id": str(flight_test_committee.id),
            "decision_type": "ESCALATE",
            "decision_text": "Escalated to the Risk Management Committee for acceptance.",
        }, headers=headers)
        assert escalation_response.status_code == 201

        risk_management_committee = db.scalar(select(Committee).where(Committee.name == "Risk Management Committee"))
        assert risk_management_committee is not None
        decision_response = client.post("/risk-decisions", json={
            "risk_record_id": risk["id"], "committee_id": str(risk_management_committee.id),
            "decision_type": "ACCEPT_RESIDUAL_RISK",
            "decision_text": "Residual risk accepted for continued monitoring after mitigation.",
        }, headers=headers)
        assert decision_response.status_code == 201
        assert decision_response.json()["decision_type"] == "ACCEPT_RESIDUAL_RISK"

        detail_response = client.get(f"/risks/{risk['id']}/detail", headers=headers)
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert len(detail["assessments"]) >= 2
        assert len(detail["actions"]) >= 1
        assert len(detail["decisions"]) >= 1
        assert any(item["calculated_score"] == 9 for item in detail["assessments"])
        assert detail["audit_summary"]["total_count"] > 0

        report_response = client.post(f"/reports/risk-dossiers/{risk['id']}", json={"output_dir": str(tmp_path)}, headers=headers)
        assert report_response.status_code == 201
        report = report_response.json()
        assert report["report_type"] == "RISK_DOSSIER_DOCX"
        assert report["generated_by_user_id"] == user["id"]
        assert report["file_path"]
        metadata_response = client.get(f"/reports/{report['id']}", headers=headers)
        assert metadata_response.status_code == 200
        assert metadata_response.json()["id"] == report["id"]
        download_response = client.get(f"/reports/{report['id']}/download", headers=headers)
        assert download_response.status_code == 200
        assert len(download_response.content) > 0

        audit_response = client.get("/audit-logs", headers=headers)
        assert audit_response.status_code == 200
        assert audit_response.json()
        assert any(item["entity_type"] in {"RiskRecord", "RiskAssessment", "RiskAction", "RiskDecision", "GeneratedReport"} for item in audit_response.json())
    finally:
        client.close()
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(engine)
