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
from app.models.committee import Committee
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
from app.models.risk import (
    RiskAction,
    RiskAssessment,
    RiskMonitoringReview,
    RiskRecord,
)
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
        email=f"risk-search-{uuid.uuid4()}@example.com",
        display_name="Risk Search User",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def _create_board(db: Session, name: str = "Search Board") -> Committee:
    board = Committee(
        name=f"{name} {uuid.uuid4()}",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=False,
        is_active=True,
    )
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def _create_risk(
    db: Session,
    *,
    creator: User,
    risk_id: str | None = None,
    problem_description: str = "Searchable risk record",
    source_trigger: str | None = None,
    system_scope: str | None = None,
    central_event: str | None = None,
    hazard_statement: str | None = None,
    domain: RiskDomain = RiskDomain.FLIGHT_TEST,
    board_of_origin_id: uuid.UUID | None = None,
    workflow_status: RiskWorkflowStatus = RiskWorkflowStatus.DRAFT,
    lifecycle_status: RiskLifecycleStatus = RiskLifecycleStatus.OPEN,
    owner_user_id: uuid.UUID | None = None,
    is_active: bool = True,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=risk_id or f"RISK-{uuid.uuid4()}",
        problem_description=problem_description,
        source_trigger=source_trigger,
        system_scope=system_scope,
        central_event=central_event,
        hazard_statement=hazard_statement,
        domain=domain,
        board_of_origin_id=board_of_origin_id,
        workflow_status=workflow_status,
        lifecycle_status=lifecycle_status,
        created_by_user_id=creator.id,
        owner_user_id=owner_user_id,
        is_active=is_active,
        archived_at=None if is_active else datetime.now(timezone.utc),
    )
    if created_at is not None:
        risk.created_at = created_at
    if updated_at is not None:
        risk.updated_at = updated_at
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


def _ids(response) -> list[str]:
    return [item["id"] for item in response.json()]


def _add_assessment(
    db: Session,
    risk: RiskRecord,
    *,
    risk_level: str,
    assessed_at: datetime,
) -> None:
    db.add(
        RiskAssessment(
            risk_record_id=risk.id,
            assessment_type=RiskAssessmentType.INITIAL,
            severity="Major",
            likelihood="Remote",
            risk_level=risk_level,
            assessed_at=assessed_at,
        )
    )
    db.commit()


def _add_action(
    db: Session,
    risk: RiskRecord,
    *,
    status: RiskActionStatus,
    due_date: date,
) -> None:
    db.add(
        RiskAction(
            risk_record_id=risk.id,
            title=f"Action {uuid.uuid4()}",
            due_date=due_date,
            status=status,
        )
    )
    db.commit()


def _add_monitoring(
    db: Session,
    risk: RiskRecord,
    *,
    status: RiskMonitoringStatus,
    is_active: bool = True,
) -> None:
    db.add(
        RiskMonitoringReview(
            risk_record_id=risk.id,
            status=status,
            is_active=is_active,
        )
    )
    db.commit()


def test_authorized_list_without_filters_returns_authorized_active_risks(
    client: TestClient, db_session: Session
) -> None:
    reader = _create_user(db_session)
    other = _create_user(db_session)
    readable = _create_risk(db_session, creator=reader)
    _create_risk(db_session, creator=other)

    response = client.get("/risks", headers=_headers(reader))

    assert response.status_code == 200
    assert _ids(response) == [str(readable.id)]


def test_include_archived_false_excludes_inactive_risks(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    active = _create_risk(db_session, creator=user)
    archived = _create_risk(db_session, creator=user, is_active=False)

    response = client.get("/risks?include_archived=false", headers=_headers(user))

    assert response.status_code == 200
    assert str(active.id) in _ids(response)
    assert str(archived.id) not in _ids(response)


def test_include_archived_true_includes_readable_archived_risks(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    active = _create_risk(db_session, creator=user)
    archived = _create_risk(db_session, creator=user, is_active=False)

    response = client.get("/risks?include_archived=true", headers=_headers(user))

    assert response.status_code == 200
    assert set(_ids(response)) == {str(active.id), str(archived.id)}


def test_search_matches_risk_id(client: TestClient, db_session: Session) -> None:
    user = _create_user(db_session)
    matched = _create_risk(db_session, creator=user, risk_id="RISK-2026-0001")
    _create_risk(db_session, creator=user, risk_id="RISK-2026-0002")

    response = client.get("/risks?search=0001", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_search_matches_problem_description(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    matched = _create_risk(
        db_session,
        creator=user,
        problem_description="Unexpected hydraulic pressure drop",
    )
    _create_risk(db_session, creator=user, problem_description="Cabin placard issue")

    response = client.get("/risks?search=hydraulic", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_search_matches_central_event_or_hazard_statement(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    event_match = _create_risk(
        db_session,
        creator=user,
        central_event="Loss of braking during rejected takeoff",
    )
    hazard_match = _create_risk(
        db_session,
        creator=user,
        hazard_statement="Thermal runaway may damage avionics",
    )
    _create_risk(db_session, creator=user, problem_description="Unrelated")

    event_response = client.get("/risks?search=braking", headers=_headers(user))
    hazard_response = client.get("/risks?search=avionics", headers=_headers(user))

    assert event_response.status_code == 200
    assert hazard_response.status_code == 200
    assert _ids(event_response) == [str(event_match.id)]
    assert _ids(hazard_response) == [str(hazard_match.id)]


def test_risk_id_partial_filter_works(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    matched = _create_risk(db_session, creator=user, risk_id="RISK-2026-0042")
    _create_risk(db_session, creator=user, risk_id="RISK-2026-0099")

    response = client.get("/risks?risk_id=0042", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_domain_filter_works(client: TestClient, db_session: Session) -> None:
    user = _create_user(db_session)
    matched = _create_risk(db_session, creator=user, domain=RiskDomain.ENGINEERING)
    _create_risk(db_session, creator=user, domain=RiskDomain.QUALITY)

    response = client.get("/risks?domain=ENGINEERING", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_board_of_origin_filter_works(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    board = _create_board(db_session)
    other_board = _create_board(db_session, "Other Board")
    matched = _create_risk(db_session, creator=user, board_of_origin_id=board.id)
    _create_risk(db_session, creator=user, board_of_origin_id=other_board.id)

    response = client.get(
        f"/risks?board_of_origin_id={board.id}",
        headers=_headers(user),
    )

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_workflow_status_filter_works(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    matched = _create_risk(
        db_session,
        creator=user,
        workflow_status=RiskWorkflowStatus.ACCEPTED,
    )
    _create_risk(db_session, creator=user, workflow_status=RiskWorkflowStatus.DRAFT)

    response = client.get("/risks?workflow_status=ACCEPTED", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_lifecycle_status_filter_works(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    matched = _create_risk(
        db_session,
        creator=user,
        lifecycle_status=RiskLifecycleStatus.MONITORING,
    )
    _create_risk(db_session, creator=user, lifecycle_status=RiskLifecycleStatus.OPEN)

    response = client.get("/risks?lifecycle_status=MONITORING", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_owner_user_id_filter_works(
    client: TestClient, db_session: Session
) -> None:
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    other_owner = _create_user(db_session)
    matched = _create_risk(db_session, creator=creator, owner_user_id=owner.id)
    _create_risk(db_session, creator=creator, owner_user_id=other_owner.id)

    response = client.get(f"/risks?owner_user_id={owner.id}", headers=_headers(creator))

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_created_by_user_id_filter_works(
    client: TestClient, db_session: Session
) -> None:
    reader = _create_user(db_session)
    other = _create_user(db_session)
    matched = _create_risk(db_session, creator=reader)
    _create_risk(db_session, creator=other, owner_user_id=reader.id)

    response = client.get(
        f"/risks?created_by_user_id={reader.id}",
        headers=_headers(reader),
    )

    assert response.status_code == 200
    assert _ids(response) == [str(matched.id)]


def test_latest_risk_level_filter_uses_latest_assessment(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    older_high_latest_low = _create_risk(db_session, creator=user)
    latest_high = _create_risk(db_session, creator=user)
    now = datetime.now(timezone.utc)
    _add_assessment(
        db_session, older_high_latest_low, risk_level="HIGH", assessed_at=now
    )
    _add_assessment(
        db_session,
        older_high_latest_low,
        risk_level="LOW",
        assessed_at=now + timedelta(hours=1),
    )
    _add_assessment(db_session, latest_high, risk_level="HIGH", assessed_at=now)

    response = client.get("/risks?latest_risk_level=HIGH", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(latest_high.id)]


def test_has_overdue_actions_true_returns_risks_with_overdue_open_actions(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    overdue = _create_risk(db_session, creator=user)
    current = _create_risk(db_session, creator=user)
    _add_action(
        db_session,
        overdue,
        status=RiskActionStatus.OPEN,
        due_date=date.today() - timedelta(days=1),
    )
    _add_action(
        db_session,
        current,
        status=RiskActionStatus.OPEN,
        due_date=date.today() + timedelta(days=1),
    )

    response = client.get("/risks?has_overdue_actions=true", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == [str(overdue.id)]


def test_has_overdue_actions_false_excludes_risks_with_overdue_open_actions(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    overdue = _create_risk(db_session, creator=user)
    no_overdue = _create_risk(db_session, creator=user)
    _add_action(
        db_session,
        overdue,
        status=RiskActionStatus.IN_PROGRESS,
        due_date=date.today() - timedelta(days=1),
    )

    response = client.get("/risks?has_overdue_actions=false", headers=_headers(user))

    assert response.status_code == 200
    assert str(no_overdue.id) in _ids(response)
    assert str(overdue.id) not in _ids(response)


def test_completed_and_cancelled_overdue_actions_do_not_count(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    completed = _create_risk(db_session, creator=user)
    cancelled = _create_risk(db_session, creator=user)
    _add_action(
        db_session,
        completed,
        status=RiskActionStatus.COMPLETED,
        due_date=date.today() - timedelta(days=1),
    )
    _add_action(
        db_session,
        cancelled,
        status=RiskActionStatus.CANCELLED,
        due_date=date.today() - timedelta(days=1),
    )

    response = client.get("/risks?has_overdue_actions=true", headers=_headers(user))

    assert response.status_code == 200
    assert _ids(response) == []


def test_has_due_or_overdue_monitoring_true_returns_due_or_overdue_active_reviews(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    due = _create_risk(db_session, creator=user)
    overdue = _create_risk(db_session, creator=user)
    active = _create_risk(db_session, creator=user)
    _add_monitoring(db_session, due, status=RiskMonitoringStatus.DUE)
    _add_monitoring(db_session, overdue, status=RiskMonitoringStatus.OVERDUE)
    _add_monitoring(db_session, active, status=RiskMonitoringStatus.ACTIVE)

    response = client.get(
        "/risks?has_due_or_overdue_monitoring=true",
        headers=_headers(user),
    )

    assert response.status_code == 200
    assert set(_ids(response)) == {str(due.id), str(overdue.id)}


def test_closed_or_cancelled_monitoring_does_not_count_as_due_or_overdue(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    closed = _create_risk(db_session, creator=user)
    cancelled = _create_risk(db_session, creator=user)
    inactive_due = _create_risk(db_session, creator=user)
    _add_monitoring(db_session, closed, status=RiskMonitoringStatus.CLOSED)
    _add_monitoring(db_session, cancelled, status=RiskMonitoringStatus.CANCELLED)
    _add_monitoring(
        db_session,
        inactive_due,
        status=RiskMonitoringStatus.DUE,
        is_active=False,
    )

    response = client.get(
        "/risks?has_due_or_overdue_monitoring=true",
        headers=_headers(user),
    )

    assert response.status_code == 200
    assert _ids(response) == []


def test_sort_by_updated_at_desc_works(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    older = _create_risk(
        db_session,
        creator=user,
        updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = _create_risk(
        db_session,
        creator=user,
        updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    response = client.get(
        "/risks?sort_by=updated_at&sort_direction=desc",
        headers=_headers(user),
    )

    assert response.status_code == 200
    assert _ids(response) == [str(newer.id), str(older.id)]


def test_sort_by_created_at_asc_works(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)
    older = _create_risk(
        db_session,
        creator=user,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = _create_risk(
        db_session,
        creator=user,
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    response = client.get(
        "/risks?sort_by=created_at&sort_direction=asc",
        headers=_headers(user),
    )

    assert response.status_code == 200
    assert _ids(response) == [str(older.id), str(newer.id)]


def test_unsupported_sort_by_returns_http_400(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)

    response = client.get("/risks?sort_by=owner_user_id", headers=_headers(user))

    assert response.status_code == 400
    assert "Unsupported sort_by" in response.json()["error"]["message"]


def test_unsupported_sort_direction_returns_http_400(
    client: TestClient, db_session: Session
) -> None:
    user = _create_user(db_session)

    response = client.get("/risks?sort_direction=sideways", headers=_headers(user))

    assert response.status_code == 400
    assert "Unsupported sort_direction" in response.json()["error"]["message"]


def test_unauthorized_matching_risk_is_not_returned(
    client: TestClient, db_session: Session
) -> None:
    reader = _create_user(db_session)
    other = _create_user(db_session)
    readable = _create_risk(
        db_session,
        creator=reader,
        problem_description="Readable hydraulic keyword",
    )
    _create_risk(
        db_session,
        creator=other,
        problem_description="Unauthorized hydraulic keyword",
    )

    response = client.get("/risks?search=hydraulic", headers=_headers(reader))

    assert response.status_code == 200
    assert _ids(response) == [str(readable.id)]
