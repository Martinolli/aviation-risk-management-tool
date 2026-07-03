import uuid
from collections.abc import Generator
from datetime import date, datetime, timedelta, timezone

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
    RiskActionStatus,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskRecord
from app.models.user import User
from app.services.auth_service import create_access_token
from app.services.risk_action_service import get_risk_action_due_status


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


def _create_risk_record(
    db_session: Session,
    *,
    created_by_user_id: uuid.UUID | None = None,
) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=created_by_user_id,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


def _action_payload(
    risk_record_id: uuid.UUID,
    *,
    title: str = "Inspect flight test instrumentation",
    action_owner_user_id: uuid.UUID | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "risk_record_id": str(risk_record_id),
        "title": title,
        "description": "Mitigation action",
        "due_date": "2026-06-30",
    }
    if action_owner_user_id is not None:
        payload["action_owner_user_id"] = str(action_owner_user_id)
    return payload


def _create_action(
    db_session: Session,
    risk_record_id: uuid.UUID,
    *,
    action_owner_user_id: uuid.UUID | None = None,
    due_date: date | None = date(2026, 6, 30),
    status: RiskActionStatus = RiskActionStatus.OPEN,
    title: str = "Inspect flight test instrumentation",
) -> RiskAction:
    action = RiskAction(
        risk_record_id=risk_record_id,
        title=title,
        description="Mitigation action",
        action_owner_user_id=action_owner_user_id,
        due_date=due_date,
        status=status,
    )
    db_session.add(action)
    db_session.commit()
    db_session.refresh(action)
    return action


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Action User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def test_get_risk_actions_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk_record = _create_risk_record(db_session, created_by_user_id=user.id)
    _create_action(db_session, risk_record.id)

    response = client.get("/risk-actions", headers=_headers(user))

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_post_risk_actions_creates_action(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.post("/risk-actions", json=_action_payload(risk_record.id))

    assert response.status_code == 201
    body = response.json()
    assert body["risk_record_id"] == str(risk_record.id)
    assert body["title"] == "Inspect flight test instrumentation"
    assert body["status"] == "OPEN"


def test_post_risk_actions_with_empty_title_returns_error(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.post(
        "/risk-actions",
        json=_action_payload(risk_record.id, title=""),
    )

    assert response.status_code in {400, 422}


def test_post_risk_actions_for_unknown_risk_returns_http_400(
    client: TestClient,
) -> None:
    response = client.post("/risk-actions", json=_action_payload(uuid.uuid4()))

    assert response.status_code == 400


def test_post_risk_action_validates_optional_owner(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    active_owner = _create_user(db_session)
    inactive_owner = _create_user(db_session, is_active=False)

    response = client.post(
        "/risk-actions",
        json=_action_payload(risk_record.id, action_owner_user_id=active_owner.id),
    )
    assert response.status_code == 201
    assert response.json()["action_owner_user_id"] == str(active_owner.id)
    assert client.post(
        "/risk-actions",
        json=_action_payload(risk_record.id, action_owner_user_id=uuid.uuid4()),
    ).status_code == 400
    assert client.post(
        "/risk-actions",
        json=_action_payload(risk_record.id, action_owner_user_id=inactive_owner.id),
    ).status_code == 400


def test_get_risk_action_returns_action(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk_record = _create_risk_record(db_session, created_by_user_id=user.id)
    action = _create_action(db_session, risk_record.id)

    response = client.get(f"/risk-actions/{action.id}", headers=_headers(user))

    assert response.status_code == 200
    assert response.json()["id"] == str(action.id)


def test_get_unknown_action_returns_http_404(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    response = client.get(
        f"/risk-actions/{uuid.uuid4()}", headers=_headers(user)
    )

    assert response.status_code == 404


def test_patch_risk_action_updates_valid_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)
    actor = _create_user(db_session)

    response = client.patch(
        f"/risk-actions/{action.id}",
        json={
            "title": "Revise inspection plan",
            "description": "Updated mitigation",
            "due_date": "2026-07-15",
            "status": "IN_PROGRESS",
        },
        headers={"X-User-Id": str(actor.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Revise inspection plan"
    assert body["description"] == "Updated mitigation"
    assert body["due_date"] == "2026-07-15"
    assert body["status"] == "IN_PROGRESS"


def test_patch_risk_action_with_status_completed_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)
    actor = _create_user(db_session)

    response = client.patch(
        f"/risk-actions/{action.id}",
        json={"status": "COMPLETED"},
        headers={"X-User-Id": str(actor.id)},
    )

    assert response.status_code == 400


def test_complete_risk_action_completes_action(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)
    actor = _create_user(db_session)

    response = client.post(
        f"/risk-actions/{action.id}/complete",
        json={"completion_notes": "Inspection completed"},
        headers={"X-User-Id": str(actor.id)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["completion_notes"] == "Inspection completed"
    assert body["completed_at"] is not None


def test_complete_risk_action_again_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(db_session, risk_record.id)
    actor = _create_user(db_session)
    action.status = RiskActionStatus.COMPLETED
    action.completed_at = datetime.now(timezone.utc)
    db_session.commit()

    response = client.post(
        f"/risk-actions/{action.id}/complete",
        json={"completion_notes": "Already done"},
        headers={"X-User-Id": str(actor.id)},
    )

    assert response.status_code == 400


def test_action_mutations_require_active_owner_or_actor(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    owner = _create_user(db_session)
    non_owner = _create_user(db_session)
    inactive_user = _create_user(db_session, is_active=False)
    action = _create_action(
        db_session,
        risk_record.id,
        action_owner_user_id=owner.id,
    )

    assert client.patch(f"/risk-actions/{action.id}", json={"title": "Updated"}).status_code == 400
    assert client.patch(
        f"/risk-actions/{action.id}",
        json={"title": "Updated"},
        headers={"X-User-Id": str(non_owner.id)},
    ).status_code == 400
    assert client.patch(
        f"/risk-actions/{action.id}",
        json={"title": "Updated"},
        headers={"X-User-Id": str(uuid.uuid4())},
    ).status_code == 401
    assert client.patch(
        f"/risk-actions/{action.id}",
        json={"title": "Updated"},
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403
    assert client.patch(
        f"/risk-actions/{action.id}",
        json={"title": "Updated"},
        headers={"X-User-Id": str(owner.id)},
    ).status_code == 200

    assert client.post(
        f"/risk-actions/{action.id}/complete", json={}
    ).status_code == 400
    assert client.post(
        f"/risk-actions/{action.id}/complete",
        json={},
        headers={"X-User-Id": str(non_owner.id)},
    ).status_code == 400
    assert client.post(
        f"/risk-actions/{action.id}/complete",
        json={},
        headers={"X-User-Id": str(uuid.uuid4())},
    ).status_code == 401
    assert client.post(
        f"/risk-actions/{action.id}/complete",
        json={},
        headers={"X-User-Id": str(inactive_user.id)},
    ).status_code == 403
    complete_response = client.post(
        f"/risk-actions/{action.id}/complete",
        json={"completion_notes": "Completed by owner"},
        headers={"X-User-Id": str(owner.id)},
    )
    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == action.id,
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "status",
        )
    )

    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "COMPLETED"
    assert audit_log is not None
    assert audit_log.changed_by_user_id == owner.id


def test_get_risk_actions_filtered_by_risk_record_id(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    first_risk = _create_risk_record(db_session, created_by_user_id=user.id)
    second_risk = _create_risk_record(db_session, created_by_user_id=user.id)
    first_action = _create_action(db_session, first_risk.id)
    _create_action(db_session, second_risk.id)

    response = client.get(
        f"/risk-actions?risk_record_id={first_risk.id}", headers=_headers(user)
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(first_action.id)


def test_user_cannot_list_or_get_actions_for_unreadable_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    unauthorized_user = _create_user(db_session)
    risk_record = _create_risk_record(
        db_session, created_by_user_id=creator.id
    )
    action = _create_action(db_session, risk_record.id)

    scoped_list = client.get(
        f"/risk-actions?risk_record_id={risk_record.id}",
        headers=_headers(unauthorized_user),
    )
    all_actions = client.get("/risk-actions", headers=_headers(unauthorized_user))
    individual = client.get(
        f"/risk-actions/{action.id}", headers=_headers(unauthorized_user)
    )

    assert scoped_list.status_code == 400
    assert all_actions.status_code == 200
    assert all_actions.json() == []
    assert individual.status_code == 400


def test_my_actions_returns_assigned_actions_without_unreadable_actions(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    other_user = _create_user(db_session)
    assigned_risk = _create_risk_record(db_session)
    unreadable_risk = _create_risk_record(
        db_session, created_by_user_id=other_user.id
    )
    assigned_action = _create_action(
        db_session,
        assigned_risk.id,
        action_owner_user_id=user.id,
        title="Assigned action",
    )
    _create_action(db_session, unreadable_risk.id, title="Unreadable action")

    response = client.get("/risk-actions/my", headers=_headers(user))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(assigned_action.id)]


def test_my_actions_status_filters_and_includes(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk_record = _create_risk_record(
        db_session, created_by_user_id=user.id
    )
    open_action = _create_action(
        db_session, risk_record.id, title="Open action"
    )
    completed_action = _create_action(
        db_session,
        risk_record.id,
        status=RiskActionStatus.COMPLETED,
        title="Completed action",
    )
    cancelled_action = _create_action(
        db_session,
        risk_record.id,
        status=RiskActionStatus.CANCELLED,
        title="Cancelled action",
    )

    default_response = client.get("/risk-actions/my", headers=_headers(user))
    completed_response = client.get(
        "/risk-actions/my?include_completed=true", headers=_headers(user)
    )
    cancelled_response = client.get(
        "/risk-actions/my?include_cancelled=true", headers=_headers(user)
    )

    assert [item["id"] for item in default_response.json()] == [str(open_action.id)]
    assert {item["id"] for item in completed_response.json()} == {
        str(open_action.id),
        str(completed_action.id),
    }
    assert {item["id"] for item in cancelled_response.json()} == {
        str(open_action.id),
        str(cancelled_action.id),
    }


def test_my_actions_orders_by_due_status(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk_record = _create_risk_record(
        db_session, created_by_user_id=user.id
    )
    today = date.today()
    action_specs = [
        ("No due date", None, RiskActionStatus.OPEN),
        ("Cancelled", today - timedelta(days=5), RiskActionStatus.CANCELLED),
        ("Open", today + timedelta(days=20), RiskActionStatus.IN_PROGRESS),
        ("Due soon", today + timedelta(days=7), RiskActionStatus.OPEN),
        ("Completed", today - timedelta(days=5), RiskActionStatus.COMPLETED),
        ("Due today", today, RiskActionStatus.OPEN),
        ("Overdue", today - timedelta(days=1), RiskActionStatus.OPEN),
    ]
    for title, due_date, action_status in action_specs:
        _create_action(
            db_session,
            risk_record.id,
            title=title,
            due_date=due_date,
            status=action_status,
        )

    response = client.get(
        "/risk-actions/my?include_completed=true&include_cancelled=true",
        headers=_headers(user),
    )

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == [
        "Overdue",
        "Due today",
        "Due soon",
        "Open",
        "No due date",
        "Completed",
        "Cancelled",
    ]


@pytest.mark.parametrize(
    ("status", "expected_due_status"),
    [
        (RiskActionStatus.COMPLETED, "COMPLETED"),
        (RiskActionStatus.CANCELLED, "CANCELLED"),
    ],
)
def test_closed_actions_with_past_due_dates_are_not_overdue(
    db_session: Session,
    status: RiskActionStatus,
    expected_due_status: str,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = _create_action(
        db_session,
        risk_record.id,
        due_date=date.today() - timedelta(days=30),
        status=status,
    )

    assert get_risk_action_due_status(action) == expected_due_status


def test_unauthenticated_user_cannot_access_my_actions(client: TestClient) -> None:
    response = client.get("/risk-actions/my")

    assert response.status_code == 400
