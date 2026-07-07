import uuid
from collections.abc import Generator
from datetime import date, datetime, timezone

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
from app.models.committee import Committee, CommitteeMember
from app.models.committee_meeting import CommitteeMeeting
from app.models.enums import (
    AuditAction,
    AuthorityLevel,
    CommitteeMeetingStatus,
    CommitteeType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskDecision, RiskRecord
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


def _headers(user: User) -> dict[str, str]:
    return {"X-User-Id": str(user.id)}


def _create_user(db: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"minutes-{uuid.uuid4()}@example.com",
        display_name="Minutes User",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _create_committee(db: Session, *, name: str | None = None) -> Committee:
    committee = Committee(
        name=name or f"Minutes Committee {uuid.uuid4()}",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=False,
        is_active=True,
    )
    db.add(committee)
    db.flush()
    return committee


def _add_member(db: Session, committee: Committee, user: User) -> None:
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
    committee: Committee,
    creator: User | None = None,
    risk_id: str = "RISK-MIN-001",
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=risk_id,
        problem_description="Flight test agenda risk",
        domain=RiskDomain.FLIGHT_TEST,
        board_of_origin_id=committee.id,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id if creator else None,
        is_active=True,
    )
    db.add(risk)
    db.flush()
    return risk


def _create_decision(
    db: Session,
    *,
    committee: Committee,
    risk: RiskRecord,
    user: User,
) -> RiskDecision:
    decision = RiskDecision(
        risk_record_id=risk.id,
        committee_id=committee.id,
        decision_type=RiskDecisionType.APPROVE,
        decision_text="Approved with monitoring.",
        decided_by_user_id=user.id,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(decision)
    db.flush()
    return decision


def _create_meeting_payload(committee: Committee, **overrides):
    payload = {
        "committee_id": str(committee.id),
        "title": "Weekly Committee Meeting Minutes",
        "meeting_date": "2026-07-07",
        "location": "SMS room",
        "agenda_summary": "Agenda Item review",
        "discussion_summary": "General discussion",
        "decisions_summary": "Decision Summary",
        "action_items_summary": "Action Items",
    }
    payload.update(overrides)
    return payload


def test_authorized_member_can_create_meeting_with_attendees_and_risk_items(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    committee = _create_committee(db_session, name="Flight Test Board")
    _add_member(db_session, committee, member)
    risk = _create_risk(db_session, committee=committee, creator=member)
    decision = _create_decision(db_session, committee=committee, risk=risk, user=member)

    response = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(
            committee,
            attendees=[
                {"user_id": str(member.id), "role_label": "Chair"},
                {"attendee_name": "External Observer", "attendance_status": "OBSERVER"},
            ],
            risk_items=[
                {
                    "risk_record_id": str(risk.id),
                    "agenda_item_number": 1,
                    "discussion_summary": "Reviewed controls.",
                    "decision_summary": "Continue monitoring.",
                    "linked_risk_decision_id": str(decision.id),
                }
            ],
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == CommitteeMeetingStatus.DRAFT
    assert body["committee_name"] == "Flight Test Board"
    assert body["authority_level"] == "LOW"
    assert len(body["attendees"]) == 2
    assert body["risk_items"][0]["risk_id"] == "RISK-MIN-001"


def test_unauthorized_user_cannot_create_or_read_meeting(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    unrelated = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee, member)

    created = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(committee),
    )
    unauthorized_create = client.post(
        "/committee-meetings",
        headers=_headers(unrelated),
        json=_create_meeting_payload(committee),
    )
    unauthorized_read = client.get(
        f"/committee-meetings/{created.json()['id']}",
        headers=_headers(unrelated),
    )

    assert created.status_code == 201
    assert unauthorized_create.status_code == 400
    assert unauthorized_read.status_code == 400


def test_meeting_title_and_attendee_identity_are_required(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee, member)
    db_session.commit()

    empty_title = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(committee, title="   "),
    )
    missing_attendee_identity = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(
            committee,
            attendees=[{"attendance_status": "PRESENT"}],
        ),
    )

    assert empty_title.status_code == 400
    assert missing_attendee_identity.status_code == 422


def test_risk_items_require_readable_risk_and_valid_linked_decision(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    other_member = _create_user(db_session)
    committee = _create_committee(db_session)
    other_committee = _create_committee(db_session)
    _add_member(db_session, committee, member)
    _add_member(db_session, other_committee, other_member)
    meeting = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(committee),
    ).json()
    readable_risk = _create_risk(
        db_session,
        committee=committee,
        creator=member,
        risk_id="RISK-READABLE",
    )
    unreadable_risk = _create_risk(
        db_session,
        committee=other_committee,
        creator=other_member,
        risk_id="RISK-UNREADABLE",
    )
    wrong_decision = _create_decision(
        db_session,
        committee=other_committee,
        risk=unreadable_risk,
        user=other_member,
    )

    unreadable_response = client.post(
        f"/committee-meetings/{meeting['id']}/risk-items",
        headers=_headers(member),
        json={"risk_record_id": str(unreadable_risk.id)},
    )
    wrong_decision_response = client.post(
        f"/committee-meetings/{meeting['id']}/risk-items",
        headers=_headers(member),
        json={
            "risk_record_id": str(readable_risk.id),
            "linked_risk_decision_id": str(wrong_decision.id),
        },
    )

    assert unreadable_response.status_code == 400
    assert wrong_decision_response.status_code == 400


def test_user_lists_only_meetings_for_their_committees(
    client: TestClient,
    db_session: Session,
) -> None:
    first_user = _create_user(db_session)
    second_user = _create_user(db_session)
    first_committee = _create_committee(db_session)
    second_committee = _create_committee(db_session)
    _add_member(db_session, first_committee, first_user)
    _add_member(db_session, second_committee, second_user)
    first = client.post(
        "/committee-meetings",
        headers=_headers(first_user),
        json=_create_meeting_payload(first_committee, title="First Meeting"),
    ).json()
    client.post(
        "/committee-meetings",
        headers=_headers(second_user),
        json=_create_meeting_payload(second_committee, title="Second Meeting"),
    )

    listed = client.get("/committee-meetings", headers=_headers(first_user))

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [first["id"]]


def test_draft_meeting_can_be_updated_and_finalized_meeting_is_read_only(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee, member)
    meeting = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(
            committee,
            attendees=[{"user_id": str(member.id)}],
        ),
    ).json()

    updated = client.patch(
        f"/committee-meetings/{meeting['id']}",
        headers=_headers(member),
        json={"title": "Updated Meeting Minutes"},
    )
    finalized = client.post(
        f"/committee-meetings/{meeting['id']}/finalize",
        headers=_headers(member),
        json={"finalization_notes": "Finalized after quorum."},
    )
    blocked_update = client.patch(
        f"/committee-meetings/{meeting['id']}",
        headers=_headers(member),
        json={"location": "New room"},
    )
    blocked_cancel = client.post(
        f"/committee-meetings/{meeting['id']}/cancel",
        headers=_headers(member),
        json={"cancellation_reason": "No quorum"},
    )

    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated Meeting Minutes"
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "FINALIZED"
    assert finalized.json()["finalized_by_user_id"] == str(member.id)
    assert finalized.json()["finalized_at"] is not None
    assert blocked_update.status_code == 400
    assert blocked_cancel.status_code == 400


def test_draft_meeting_can_add_update_remove_attendee_and_risk_item(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee, member)
    risk = _create_risk(db_session, committee=committee, creator=member)
    meeting = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(committee),
    ).json()

    attendee_added = client.post(
        f"/committee-meetings/{meeting['id']}/attendees",
        headers=_headers(member),
        json={"attendee_name": "Observer", "attendance_status": "OBSERVER"},
    ).json()
    attendee_id = attendee_added["attendees"][0]["id"]
    attendee_updated = client.patch(
        f"/committee-meetings/{meeting['id']}/attendees/{attendee_id}",
        headers=_headers(member),
        json={"notes": "Joined remotely."},
    ).json()
    attendee_removed = client.delete(
        f"/committee-meetings/{meeting['id']}/attendees/{attendee_id}",
        headers=_headers(member),
    ).json()

    risk_added = client.post(
        f"/committee-meetings/{meeting['id']}/risk-items",
        headers=_headers(member),
        json={"risk_record_id": str(risk.id), "agenda_item_number": 2},
    ).json()
    risk_item_id = risk_added["risk_items"][0]["id"]
    risk_updated = client.patch(
        f"/committee-meetings/{meeting['id']}/risk-items/{risk_item_id}",
        headers=_headers(member),
        json={"decision_summary": "Decision Summary", "follow_up_required": True},
    ).json()
    risk_removed = client.delete(
        f"/committee-meetings/{meeting['id']}/risk-items/{risk_item_id}",
        headers=_headers(member),
    ).json()

    assert attendee_updated["attendees"][0]["notes"] == "Joined remotely."
    assert attendee_removed["attendees"] == []
    assert risk_updated["risk_items"][0]["follow_up_required"] is True
    assert risk_removed["risk_items"] == []


def test_finalize_requires_attendance_and_draft_can_be_cancelled(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee, member)
    meeting = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(committee),
    ).json()

    finalize_without_attendance = client.post(
        f"/committee-meetings/{meeting['id']}/finalize",
        headers=_headers(member),
        json={},
    )
    cancelled = client.post(
        f"/committee-meetings/{meeting['id']}/cancel",
        headers=_headers(member),
        json={"cancellation_reason": "No quorum"},
    )

    assert finalize_without_attendance.status_code == 400
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancellation_reason"] == "No quorum"


def test_audit_records_are_created_for_create_finalize_and_cancel(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    committee = _create_committee(db_session)
    _add_member(db_session, committee, member)
    finalized_meeting = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(
            committee,
            attendees=[{"user_id": str(member.id)}],
        ),
    ).json()
    cancelled_meeting = client.post(
        "/committee-meetings",
        headers=_headers(member),
        json=_create_meeting_payload(committee, title="Cancelled Minutes"),
    ).json()

    client.post(
        f"/committee-meetings/{finalized_meeting['id']}/finalize",
        headers=_headers(member),
        json={},
    )
    client.post(
        f"/committee-meetings/{cancelled_meeting['id']}/cancel",
        headers=_headers(member),
        json={"cancellation_reason": "Cancelled"},
    )

    logs = list(
        db_session.scalars(
            select(AuditLog).where(AuditLog.entity_type == "CommitteeMeeting")
        ).all()
    )

    assert any(log.action == AuditAction.CREATE for log in logs)
    status_changes = [log for log in logs if log.field_name == "status"]
    assert {log.entity_id for log in status_changes} == {
        uuid.UUID(finalized_meeting["id"]),
        uuid.UUID(cancelled_meeting["id"]),
    }
    assert db_session.get(CommitteeMeeting, uuid.UUID(finalized_meeting["id"])) is not None
