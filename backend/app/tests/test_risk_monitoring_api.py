import uuid
from collections.abc import Generator
from datetime import date, timedelta

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
from app.models.enums import (
    AuditAction,
    RiskDomain,
    RiskLifecycleStatus,
    RiskMonitoringStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskMonitoringReview, RiskRecord
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


def _create_user(db: Session) -> User:
    user = User(
        email=f"monitoring-{uuid.uuid4()}@example.com",
        display_name="Monitoring User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_risk(
    db: Session,
    *,
    creator: User,
    lifecycle_status: RiskLifecycleStatus = RiskLifecycleStatus.OPEN,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=f"RISK-{uuid.uuid4()}",
        problem_description="Monitoring API test risk",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.ACCEPTED,
        lifecycle_status=lifecycle_status,
        created_by_user_id=creator.id,
        is_active=True,
    )
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def _create_review(
    client: TestClient,
    risk: RiskRecord,
    user: User,
    *,
    next_review_date: date | None = None,
):
    return client.post(
        "/risk-monitoring",
        headers=_headers(user),
        json={
            "risk_record_id": str(risk.id),
            "monitoring_owner_user_id": str(user.id),
            "review_frequency": "Monthly",
            "next_review_date": (
                next_review_date.isoformat() if next_review_date else None
            ),
            "review_notes": "Monitor mitigation effectiveness.",
        },
    )


def test_authorized_user_creates_and_lists_monitoring_review(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)

    created = _create_review(
        client, risk, user, next_review_date=date.today() + timedelta(days=30)
    )
    listed = client.get(
        f"/risk-monitoring/risk/{risk.id}", headers=_headers(user)
    )

    assert created.status_code == 201
    assert created.json()["created_by_user_id"] == str(user.id)
    assert created.json()["status"] == "ACTIVE"
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [created.json()["id"]]


def test_first_monitoring_review_moves_open_risk_to_monitoring(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)

    assert _create_review(client, risk, user).status_code == 201
    db_session.refresh(risk)

    assert risk.lifecycle_status == RiskLifecycleStatus.MONITORING
    assert risk.workflow_status == RiskWorkflowStatus.ACCEPTED


def test_monitoring_creation_does_not_reopen_closed_risk(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(
        db_session, creator=user, lifecycle_status=RiskLifecycleStatus.CLOSED
    )

    assert _create_review(client, risk, user).status_code == 201
    db_session.refresh(risk)
    assert risk.lifecycle_status == RiskLifecycleStatus.CLOSED


@pytest.mark.parametrize(
    ("day_offset", "expected_status"),
    [(-1, "OVERDUE"), (0, "DUE"), (1, "ACTIVE")],
)
def test_next_review_date_sets_status(
    client: TestClient,
    db_session: Session,
    day_offset: int,
    expected_status: str,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)

    response = _create_review(
        client,
        risk,
        user,
        next_review_date=date.today() + timedelta(days=day_offset),
    )

    assert response.status_code == 201
    assert response.json()["status"] == expected_status


def test_authorized_user_updates_monitoring_review(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    review = _create_review(client, risk, user).json()

    response = client.patch(
        f"/risk-monitoring/{review['id']}",
        headers=_headers(user),
        json={
            "review_frequency": "Quarterly",
            "next_review_date": date.today().isoformat(),
        },
    )

    assert response.status_code == 200
    assert response.json()["review_frequency"] == "Quarterly"
    assert response.json()["status"] == "DUE"


def test_complete_records_effectiveness_review_and_reviewer(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    review = _create_review(client, risk, user).json()

    response = client.post(
        f"/risk-monitoring/{review['id']}/complete",
        headers=_headers(user),
        json={
            "effectiveness_review": "Controls remain effective.",
            "review_outcome": "EFFECTIVE_CONTROLS",
            "next_review_date": (date.today() + timedelta(days=30)).isoformat(),
            "review_notes": "Continue monthly checks.",
        },
    )

    assert response.status_code == 200
    assert response.json()["effectiveness_review"] == "Controls remain effective."
    assert response.json()["reviewed_by_user_id"] == str(user.id)
    assert response.json()["last_reviewed_at"] is not None
    assert response.json()["status"] == "ACTIVE"


def test_close_monitoring_outcome_sets_closure_fields(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    review = _create_review(client, risk, user).json()

    response = client.post(
        f"/risk-monitoring/{review['id']}/complete",
        headers=_headers(user),
        json={
            "effectiveness_review": "No further monitoring is required.",
            "review_outcome": "CLOSE_MONITORING",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"
    assert response.json()["closed_at"] is not None
    assert response.json()["closed_by_user_id"] == str(user.id)


def test_close_endpoint_sets_status_and_reason(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    review = _create_review(client, risk, user).json()

    response = client.post(
        f"/risk-monitoring/{review['id']}/close",
        headers=_headers(user),
        json={"closure_reason": "Monitoring objective achieved."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"
    assert response.json()["is_active"] is True
    assert response.json()["closed_by_user_id"] == str(user.id)
    assert response.json()["closure_reason"] == "Monitoring objective achieved."


def test_unauthenticated_user_cannot_use_monitoring_endpoints(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    review = _create_review(client, risk, user).json()

    responses = [
        client.post("/risk-monitoring", json={"risk_record_id": str(risk.id)}),
        client.get(f"/risk-monitoring/risk/{risk.id}"),
        client.patch(f"/risk-monitoring/{review['id']}", json={}),
        client.post(
            f"/risk-monitoring/{review['id']}/complete",
            json={
                "effectiveness_review": "Review",
                "review_outcome": "CONTINUE_MONITORING",
            },
        ),
        client.post(f"/risk-monitoring/{review['id']}/close", json={}),
    ]

    assert [response.status_code for response in responses] == [400] * 5


def test_unrelated_user_cannot_use_monitoring_endpoints(
    client: TestClient, db_session: Session
) -> None:
    creator = _create_user(db_session)
    unrelated = _create_user(db_session)
    risk = _create_risk(db_session, creator=creator)
    review = _create_review(client, risk, creator).json()
    headers = _headers(unrelated)

    responses = [
        client.post(
            "/risk-monitoring",
            headers=headers,
            json={"risk_record_id": str(risk.id)},
        ),
        client.get(f"/risk-monitoring/risk/{risk.id}", headers=headers),
        client.patch(
            f"/risk-monitoring/{review['id']}", headers=headers, json={}
        ),
        client.post(
            f"/risk-monitoring/{review['id']}/complete",
            headers=headers,
            json={
                "effectiveness_review": "Review",
                "review_outcome": "CONTINUE_MONITORING",
            },
        ),
        client.post(
            f"/risk-monitoring/{review['id']}/close", headers=headers, json={}
        ),
    ]

    assert [response.status_code for response in responses] == [400] * 5


def test_risk_detail_includes_monitoring_reviews(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    review = _create_review(client, risk, user).json()

    response = client.get(f"/risks/{risk.id}/detail", headers=_headers(user))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["monitoring_reviews"]] == [
        review["id"]
    ]


def test_create_update_complete_and_close_create_audit_logs(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    completed_review = _create_review(client, risk, user).json()
    client.patch(
        f"/risk-monitoring/{completed_review['id']}",
        headers=_headers(user),
        json={"review_frequency": "Quarterly"},
    )
    client.post(
        f"/risk-monitoring/{completed_review['id']}/complete",
        headers=_headers(user),
        json={
            "effectiveness_review": "Controls effective.",
            "review_outcome": "EFFECTIVE_CONTROLS",
        },
    )
    closed_review = _create_review(client, risk, user).json()
    client.post(
        f"/risk-monitoring/{closed_review['id']}/close",
        headers=_headers(user),
        json={"closure_reason": "Complete"},
    )

    completed_logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "RiskMonitoringReview",
                AuditLog.entity_id == uuid.UUID(completed_review["id"]),
            )
        )
    )
    closed_logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "RiskMonitoringReview",
                AuditLog.entity_id == uuid.UUID(closed_review["id"]),
            )
        )
    )

    assert completed_logs[0].action == AuditAction.CREATE
    assert any(log.field_name == "review_frequency" for log in completed_logs)
    assert any(log.field_name == "effectiveness_review" for log in completed_logs)
    assert closed_logs[0].action == AuditAction.CREATE
    assert any(log.field_name == "closure_reason" for log in closed_logs)
    assert all(
        log.action in {AuditAction.CREATE, AuditAction.UPDATE}
        for log in completed_logs + closed_logs
    )


def test_list_orders_active_by_next_review_date_before_closed(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    later = _create_review(
        client, risk, user, next_review_date=date.today() + timedelta(days=10)
    ).json()
    sooner = _create_review(
        client, risk, user, next_review_date=date.today() + timedelta(days=2)
    ).json()
    closed = _create_review(
        client, risk, user, next_review_date=date.today() + timedelta(days=1)
    ).json()
    client.post(
        f"/risk-monitoring/{closed['id']}/close",
        headers=_headers(user),
        json={},
    )

    response = client.get(
        f"/risk-monitoring/risk/{risk.id}", headers=_headers(user)
    )

    assert [item["id"] for item in response.json()] == [
        sooner["id"],
        later["id"],
        closed["id"],
    ]
    assert db_session.get(
        RiskMonitoringReview, uuid.UUID(closed["id"])
    ).status == RiskMonitoringStatus.CLOSED
