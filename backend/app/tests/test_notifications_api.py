import uuid
from collections.abc import Generator
from datetime import date, timedelta

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
from app.models.committee_meeting import CommitteeMeeting
from app.models.enums import (
    AuthorityLevel,
    CommitteeMeetingStatus,
    CommitteeType,
    RiskActionStatus,
    RiskDomain,
    RiskLifecycleStatus,
    RiskMonitoringStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskMonitoringReview, RiskRecord
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
        email=f"notifications-{uuid.uuid4()}@example.com",
        display_name="Notifications User",
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
        name=name or f"Notifications Committee {uuid.uuid4()}",
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
    workflow_status: RiskWorkflowStatus = RiskWorkflowStatus.DRAFT,
    risk_id: str | None = None,
    domain: RiskDomain = RiskDomain.FLIGHT_TEST,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=risk_id or f"RISK-{uuid.uuid4().hex[:8]}",
        problem_description="Notification risk",
        domain=domain,
        board_of_origin_id=committee.id if committee else None,
        workflow_status=workflow_status,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=user.id if user else None,
        is_active=True,
    )
    db.add(risk)
    db.flush()
    return risk


def _create_action(
    db: Session,
    *,
    risk: RiskRecord,
    title: str,
    due_date: date | None,
    status: RiskActionStatus = RiskActionStatus.OPEN,
) -> RiskAction:
    action = RiskAction(
        risk_record_id=risk.id,
        title=title,
        description="Notification action",
        due_date=due_date,
        status=status,
    )
    db.add(action)
    db.flush()
    return action


def _create_monitoring(
    db: Session,
    *,
    risk: RiskRecord,
    next_review_date: date,
    status: RiskMonitoringStatus,
    is_active: bool = True,
) -> RiskMonitoringReview:
    review = RiskMonitoringReview(
        risk_record_id=risk.id,
        next_review_date=next_review_date,
        status=status,
        is_active=is_active,
    )
    db.add(review)
    db.flush()
    return review


def _create_meeting(
    db: Session,
    *,
    committee: Committee,
    meeting_date: date,
    status: CommitteeMeetingStatus = CommitteeMeetingStatus.DRAFT,
    title: str = "Notification Meeting Minutes",
) -> CommitteeMeeting:
    meeting = CommitteeMeeting(
        committee_id=committee.id,
        title=title,
        meeting_date=meeting_date,
        status=status,
        is_active=True,
    )
    db.add(meeting)
    db.flush()
    return meeting


def _fetch(
    client: TestClient,
    user: User,
    *,
    include_info: bool = True,
    limit: int = 50,
):
    return client.get(
        f"/notifications/my?include_info={str(include_info).lower()}&limit={limit}",
        headers=_headers(user),
    )


def _titles(body: dict) -> list[str]:
    return [item["title"] for item in body["items"]]


def test_authenticated_user_can_fetch_notifications(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    db_session.commit()

    response = _fetch(client, user)

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_unauthenticated_user_cannot_fetch_notifications(client: TestClient) -> None:
    response = client.get("/notifications/my")

    assert response.status_code == 400


def test_inactive_user_cannot_fetch_notifications(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive_user = _create_user(db_session, is_active=False)
    db_session.commit()

    response = _fetch(client, inactive_user)

    assert response.status_code == 403


def test_overdue_action_creates_critical_action_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    action = _create_action(
        db_session,
        risk=risk,
        title="Past due action",
        due_date=date.today() - timedelta(days=1),
    )
    db_session.commit()

    item = _fetch(client, user).json()["items"][0]

    assert item["category"] == "ACTION"
    assert item["severity"] == "CRITICAL"
    assert item["title"] == "Overdue Action"
    assert item["target_id"] == str(action.id)
    assert item["action_url"] == f"/risks/{risk.id}"


def test_due_today_action_creates_warning_action_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        title="Due today action",
        due_date=date.today(),
    )
    db_session.commit()

    item = _fetch(client, user).json()["items"][0]

    assert item["severity"] == "WARNING"
    assert item["title"] == "Action Due Today"


def test_due_soon_action_creates_info_action_when_include_info_true(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        title="Due soon action",
        due_date=date.today() + timedelta(days=3),
    )
    db_session.commit()

    body = _fetch(client, user, include_info=True).json()

    assert _titles(body) == ["Action Due Soon"]
    assert body["items"][0]["severity"] == "INFO"


def test_due_soon_action_excluded_when_include_info_false(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        title="Due soon action",
        due_date=date.today() + timedelta(days=3),
    )
    db_session.commit()

    assert _fetch(client, user, include_info=False).json()["items"] == []


@pytest.mark.parametrize(
    "status",
    [RiskActionStatus.COMPLETED, RiskActionStatus.CANCELLED],
)
def test_completed_and_cancelled_actions_do_not_create_notifications(
    client: TestClient,
    db_session: Session,
    status: RiskActionStatus,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        title=f"{status.value} action",
        due_date=date.today() - timedelta(days=5),
        status=status,
    )
    db_session.commit()

    assert _fetch(client, user).json()["items"] == []


def test_overdue_monitoring_creates_critical_monitoring_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user, risk_id="RISK-MON-OVERDUE")
    _create_monitoring(
        db_session,
        risk=risk,
        next_review_date=date.today() - timedelta(days=1),
        status=RiskMonitoringStatus.OVERDUE,
    )
    db_session.commit()

    item = _fetch(client, user).json()["items"][0]

    assert item["category"] == "MONITORING"
    assert item["severity"] == "CRITICAL"
    assert item["title"] == "Monitoring Overdue"
    assert item["risk_id"] == "RISK-MON-OVERDUE"


def test_due_monitoring_creates_warning_monitoring_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_monitoring(
        db_session,
        risk=risk,
        next_review_date=date.today(),
        status=RiskMonitoringStatus.DUE,
    )
    db_session.commit()

    item = _fetch(client, user).json()["items"][0]

    assert item["severity"] == "WARNING"
    assert item["title"] == "Monitoring Due"


@pytest.mark.parametrize(
    "status",
    [RiskMonitoringStatus.CLOSED, RiskMonitoringStatus.CANCELLED],
)
def test_closed_and_cancelled_monitoring_do_not_create_notifications(
    client: TestClient,
    db_session: Session,
    status: RiskMonitoringStatus,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_monitoring(
        db_session,
        risk=risk,
        next_review_date=date.today() - timedelta(days=2),
        status=status,
    )
    db_session.commit()

    assert _fetch(client, user).json()["items"] == []


def test_decision_queue_risk_creates_decision_queue_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    committee = _create_committee(
        db_session,
        name=INDUSTRIAL_COMMITTEE,
        authority_level=AuthorityLevel.LOW,
    )
    _add_member(db_session, committee=committee, user=user)
    risk = _create_risk(
        db_session,
        committee=committee,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        domain=RiskDomain.QUALITY,
        risk_id="RISK-QUEUE",
    )
    db_session.commit()

    item = _fetch(client, user, include_info=False).json()["items"][0]

    assert item["category"] == "DECISION_QUEUE"
    assert item["title"] == "Committee Review Pending"
    assert item["target_id"] == str(risk.id)
    assert item["committee_name"] == INDUSTRIAL_COMMITTEE


def test_draft_meeting_minutes_after_meeting_date_creates_warning_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee=committee, user=user)
    _create_meeting(
        db_session,
        committee=committee,
        meeting_date=date.today() - timedelta(days=1),
    )
    db_session.commit()

    item = _fetch(client, user, include_info=True).json()["items"][0]

    assert item["category"] == "MEETING"
    assert item["severity"] == "WARNING"
    assert item["title"] == "Meeting Minutes Draft"


def test_draft_meeting_minutes_on_meeting_date_creates_info_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee=committee, user=user)
    _create_meeting(db_session, committee=committee, meeting_date=date.today())
    db_session.commit()

    item = _fetch(client, user, include_info=True).json()["items"][0]

    assert item["severity"] == "INFO"
    assert item["title"] == "Meeting Minutes Draft"


def test_finalized_meeting_does_not_create_notification(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee=committee, user=user)
    _create_meeting(
        db_session,
        committee=committee,
        meeting_date=date.today() - timedelta(days=1),
        status=CommitteeMeetingStatus.FINALIZED,
    )
    db_session.commit()

    assert _fetch(client, user).json()["items"] == []


def test_user_cannot_see_notifications_for_unreadable_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    other_user = _create_user(db_session)
    risk = _create_risk(db_session, user=other_user)
    _create_action(
        db_session,
        risk=risk,
        title="Unreadable overdue action",
        due_date=date.today() - timedelta(days=1),
    )
    db_session.commit()

    assert _fetch(client, user).json()["items"] == []


def test_user_cannot_see_notifications_for_committee_where_not_member(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    other_user = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee=committee, user=other_user)
    _create_meeting(
        db_session,
        committee=committee,
        meeting_date=date.today() - timedelta(days=1),
    )
    db_session.commit()

    assert _fetch(client, user).json()["items"] == []


def test_summary_counts_match_returned_items(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        title="Overdue action",
        due_date=date.today() - timedelta(days=1),
    )
    _create_monitoring(
        db_session,
        risk=risk,
        next_review_date=date.today(),
        status=RiskMonitoringStatus.DUE,
    )
    db_session.commit()

    body = _fetch(client, user, include_info=False).json()

    assert body["total_count"] == len(body["items"])
    assert body["critical_count"] == 1
    assert body["warning_count"] == 1
    assert body["action_count"] == 1
    assert body["monitoring_count"] == 1


def test_notifications_are_sorted_by_severity_and_urgency(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    _create_action(
        db_session,
        risk=risk,
        title="Due soon action",
        due_date=date.today() + timedelta(days=2),
    )
    _create_action(
        db_session,
        risk=risk,
        title="Due today action",
        due_date=date.today(),
    )
    _create_action(
        db_session,
        risk=risk,
        title="Overdue action",
        due_date=date.today() - timedelta(days=1),
    )
    db_session.commit()

    body = _fetch(client, user, include_info=True).json()

    assert _titles(body) == ["Overdue Action", "Action Due Today", "Action Due Soon"]
    assert [item["severity"] for item in body["items"]] == [
        "CRITICAL",
        "WARNING",
        "INFO",
    ]


def test_limit_parameter_limits_items(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, user=user)
    for index in range(3):
        _create_action(
            db_session,
            risk=risk,
            title=f"Overdue action {index}",
            due_date=date.today() - timedelta(days=index + 1),
        )
    db_session.commit()

    body = _fetch(client, user, limit=2).json()

    assert body["total_count"] == 2
    assert len(body["items"]) == 2
