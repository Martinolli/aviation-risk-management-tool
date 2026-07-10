import uuid
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone

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
from app.models.enums import (
    AuthorityLevel,
    CommitteeType,
    RiskActionStatus,
    RiskAssessmentType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskMonitoringStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskAssessment, RiskMonitoringReview, RiskRecord
from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.decision_queue_service import INDUSTRIAL_COMMITTEE


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


def _create_user(db: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"management-{uuid.uuid4()}@example.com",
        display_name="Management User",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def _create_committee(
    db: Session,
    *,
    name: str | None = None,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
) -> Committee:
    committee = Committee(
        name=name or f"Management Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=(
            CommitteeType.OPERATIONAL_BOARD
            if authority_level == AuthorityLevel.LOW
            else CommitteeType.RISK_MANAGEMENT_COMMITTEE
        ),
        is_fixed=authority_level != AuthorityLevel.LOW,
        is_active=True,
    )
    db.add(committee)
    db.flush()
    return committee


def _add_member(db: Session, *, committee: Committee, user: User) -> None:
    db.add(
        CommitteeMember(
            committee_id=committee.id,
            user_id=user.id,
            role_label="Committee Member",
            is_active=True,
        )
    )
    db.flush()


def _create_risk(
    db: Session,
    *,
    user: User | None = None,
    committee: Committee | None = None,
    risk_id: str | None = None,
    domain: RiskDomain = RiskDomain.FLIGHT_TEST,
    workflow_status: RiskWorkflowStatus = RiskWorkflowStatus.DRAFT,
    lifecycle_status: RiskLifecycleStatus = RiskLifecycleStatus.OPEN,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=risk_id or f"RISK-{uuid.uuid4().hex[:8]}",
        problem_description="Management dashboard risk",
        domain=domain,
        board_of_origin_id=committee.id if committee else None,
        workflow_status=workflow_status,
        lifecycle_status=lifecycle_status,
        created_by_user_id=user.id if user else None,
        is_active=True,
    )
    db.add(risk)
    db.flush()
    return risk


def _create_assessment(
    db: Session,
    *,
    risk: RiskRecord,
    risk_level: str,
    assessed_at: datetime | None = None,
) -> RiskAssessment:
    assessment = RiskAssessment(
        risk_record_id=risk.id,
        assessment_type=RiskAssessmentType.INITIAL,
        severity="S4",
        likelihood="L3",
        risk_level=risk_level,
        assessed_at=assessed_at or datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.flush()
    return assessment


def _create_action(
    db: Session,
    *,
    risk: RiskRecord,
    status: RiskActionStatus = RiskActionStatus.OPEN,
    due_date: date | None = None,
) -> RiskAction:
    action = RiskAction(
        risk_record_id=risk.id,
        title="Management dashboard action",
        description="Control follow-up",
        status=status,
        due_date=due_date,
    )
    db.add(action)
    db.flush()
    return action


def _create_monitoring(
    db: Session,
    *,
    risk: RiskRecord,
    status: RiskMonitoringStatus,
    is_active: bool = True,
) -> RiskMonitoringReview:
    review = RiskMonitoringReview(
        risk_record_id=risk.id,
        next_review_date=date.today(),
        status=status,
        is_active=is_active,
    )
    db.add(review)
    db.flush()
    return review


def _get_dashboard(client: TestClient, user: User, *, limit: int = 10):
    return client.get(f"/management-dashboard?limit={limit}", headers=_headers(user))


def _kpi(body: dict, key: str) -> int:
    return next(item["value"] for item in body["kpis"] if item["key"] == key)


def test_authenticated_user_can_fetch_management_dashboard(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    response = _get_dashboard(client, user)

    assert response.status_code == 200
    assert response.json()["kpis"]


def test_unauthenticated_user_cannot_fetch_management_dashboard(
    client: TestClient,
) -> None:
    response = client.get("/management-dashboard")

    assert response.status_code == 400


def test_inactive_user_cannot_fetch_management_dashboard(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive_user = _create_user(db_session, is_active=False)
    db_session.commit()

    response = _get_dashboard(client, inactive_user)

    assert response.status_code == 403


def test_dashboard_only_includes_readable_risks(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    other_user = _create_user(db_session)
    readable = _create_risk(db_session, user=user, risk_id="RISK-READ")
    unreadable = _create_risk(db_session, user=other_user, risk_id="RISK-HIDDEN")
    _create_assessment(db_session, risk=readable, risk_level="HIGH")
    _create_assessment(db_session, risk=unreadable, risk_level="HIGH")
    db_session.commit()

    body = _get_dashboard(client, user).json()

    assert _kpi(body, "total_open_risks") == 1
    assert [item["risk_id"] for item in body["high_exposure_risks"]] == ["RISK-READ"]


def test_total_open_risks_kpi_counts_open_readable_risks(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    _create_risk(db_session, user=user)
    _create_risk(db_session, user=user, lifecycle_status=RiskLifecycleStatus.CLOSED)
    _create_risk(db_session, user=user, workflow_status=RiskWorkflowStatus.CLOSED)
    db_session.commit()

    assert _kpi(_get_dashboard(client, user).json(), "total_open_risks") == 1


def test_high_risk_exposure_kpi_counts_latest_high_extreme_critical_risks(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    for risk_level in ["HIGH", "EXTREME", "CRITICAL", "LOW"]:
        risk = _create_risk(db_session, user=user, risk_id=f"RISK-{risk_level}")
        _create_assessment(db_session, risk=risk, risk_level=risk_level)
    db_session.commit()

    body = _get_dashboard(client, user).json()

    assert _kpi(body, "high_risk_exposure") == 3
    assert {item["risk_id"] for item in body["high_exposure_risks"]} == {
        "RISK-HIGH",
        "RISK-EXTREME",
        "RISK-CRITICAL",
    }


def test_latest_assessment_is_used_when_multiple_assessments_exist(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user, risk_id="RISK-LATEST")
    _create_assessment(
        db_session,
        risk=risk,
        risk_level="LOW",
        assessed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    _create_assessment(
        db_session,
        risk=risk,
        risk_level="HIGH",
        assessed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    db_session.commit()

    body = _get_dashboard(client, user).json()

    assert _kpi(body, "high_risk_exposure") == 1
    assert body["high_exposure_risks"][0]["latest_risk_level"] == "HIGH"


def test_not_assessed_risks_appear_in_risk_level_distribution(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    _create_risk(db_session, user=user)
    db_session.commit()

    distribution = _get_dashboard(client, user).json()["risk_level_distribution"]

    assert distribution == [{"key": "NOT_ASSESSED", "label": "Not assessed", "count": 1}]


def test_domain_hotspots_count_open_risks_by_domain(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    _create_risk(db_session, user=user, domain=RiskDomain.FLIGHT_TEST)
    _create_risk(db_session, user=user, domain=RiskDomain.FLIGHT_TEST)
    _create_risk(db_session, user=user, domain=RiskDomain.QUALITY)
    db_session.commit()

    hotspots = _get_dashboard(client, user).json()["domain_hotspots"]

    assert hotspots[0] == {"key": "FLIGHT_TEST", "label": "FLIGHT_TEST", "count": 2}
    assert hotspots[1] == {"key": "QUALITY", "label": "QUALITY", "count": 1}


def test_escalated_risk_kpi_counts_rmc_and_executive_statuses(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    for workflow_status in [
        RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
        RiskWorkflowStatus.UNDER_RISK_MANAGEMENT_COMMITTEE_REVIEW,
        RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
        RiskWorkflowStatus.UNDER_EXECUTIVE_COMMITTEE_REVIEW,
        RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
    ]:
        _create_risk(db_session, user=user, workflow_status=workflow_status)
    db_session.commit()

    assert _kpi(_get_dashboard(client, user).json(), "escalated_risks") == 4


def test_accepted_monitoring_kpi_counts_accepted_or_monitoring_risks(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    _create_risk(db_session, user=user, workflow_status=RiskWorkflowStatus.ACCEPTED)
    _create_risk(db_session, user=user, lifecycle_status=RiskLifecycleStatus.MONITORING)
    _create_risk(db_session, user=user)
    db_session.commit()

    assert _kpi(_get_dashboard(client, user).json(), "accepted_monitoring") == 2


def test_overdue_action_kpi_counts_only_open_in_progress_overdue_actions(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        status=RiskActionStatus.OPEN,
        due_date=date.today() - timedelta(days=1),
    )
    _create_action(
        db_session,
        risk=risk,
        status=RiskActionStatus.IN_PROGRESS,
        due_date=date.today() - timedelta(days=2),
    )
    _create_action(
        db_session,
        risk=risk,
        status=RiskActionStatus.OPEN,
        due_date=date.today(),
    )
    db_session.commit()

    body = _get_dashboard(client, user).json()

    assert _kpi(body, "overdue_actions") == 2
    assert len(body["overdue_action_risks"]) == 1


@pytest.mark.parametrize(
    "status",
    [RiskActionStatus.COMPLETED, RiskActionStatus.CANCELLED],
)
def test_completed_cancelled_overdue_actions_do_not_count(
    client: TestClient,
    db_session: Session,
    status: RiskActionStatus,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        status=status,
        due_date=date.today() - timedelta(days=1),
    )
    db_session.commit()

    assert _kpi(_get_dashboard(client, user).json(), "overdue_actions") == 0


def test_monitoring_concerns_kpi_counts_due_overdue_active_reviews(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_monitoring(db_session, risk=risk, status=RiskMonitoringStatus.DUE)
    _create_monitoring(db_session, risk=risk, status=RiskMonitoringStatus.OVERDUE)
    _create_monitoring(db_session, risk=risk, status=RiskMonitoringStatus.ACTIVE)
    db_session.commit()

    body = _get_dashboard(client, user).json()

    assert _kpi(body, "monitoring_concerns") == 2
    assert len(body["monitoring_concern_risks"]) == 1


@pytest.mark.parametrize(
    "status",
    [RiskMonitoringStatus.CLOSED, RiskMonitoringStatus.CANCELLED],
)
def test_closed_cancelled_monitoring_reviews_do_not_count(
    client: TestClient,
    db_session: Session,
    status: RiskMonitoringStatus,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_monitoring(db_session, risk=risk, status=status)
    db_session.commit()

    assert _kpi(_get_dashboard(client, user).json(), "monitoring_concerns") == 0


def test_committee_backlog_risks_are_included_for_committee_members_only(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    outsider = _create_user(db_session)
    committee = _create_committee(
        db_session,
        name=INDUSTRIAL_COMMITTEE,
        authority_level=AuthorityLevel.LOW,
    )
    _add_member(db_session, committee=committee, user=member)
    risk = _create_risk(
        db_session,
        committee=committee,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        domain=RiskDomain.QUALITY,
        risk_id="RISK-BACKLOG",
    )
    db_session.commit()

    member_body = _get_dashboard(client, member).json()
    outsider_body = _get_dashboard(client, outsider).json()

    assert _kpi(member_body, "committee_backlog") == 1
    assert member_body["committee_backlog_risks"][0]["risk_record_id"] == str(risk.id)
    assert _kpi(outsider_body, "committee_backlog") == 0
    assert outsider_body["committee_backlog_risks"] == []


def test_top_attention_items_are_included_from_notification_service(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user, risk_id="RISK-ATTENTION")
    _create_action(
        db_session,
        risk=risk,
        status=RiskActionStatus.OPEN,
        due_date=date.today() - timedelta(days=1),
    )
    db_session.commit()

    body = _get_dashboard(client, user).json()

    assert body["top_attention_items"][0]["title"] == "Overdue Action"
    assert body["top_attention_items"][0]["risk_id"] == "RISK-ATTENTION"


def test_limit_parameter_limits_management_risk_lists(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    for index in range(3):
        risk = _create_risk(db_session, user=user, risk_id=f"RISK-LIMIT-{index}")
        _create_assessment(db_session, risk=risk, risk_level="HIGH")
        _create_action(
            db_session,
            risk=risk,
            due_date=date.today() - timedelta(days=index + 1),
        )
        _create_monitoring(db_session, risk=risk, status=RiskMonitoringStatus.DUE)
    db_session.commit()

    body = _get_dashboard(client, user, limit=2).json()

    assert len(body["high_exposure_risks"]) == 2
    assert len(body["overdue_action_risks"]) == 2
    assert len(body["monitoring_concern_risks"]) == 2
