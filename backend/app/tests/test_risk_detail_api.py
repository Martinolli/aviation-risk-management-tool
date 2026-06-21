import uuid
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import (
    AuditAction,
    AuthorityLevel,
    CommitteeType,
    RiskActionStatus,
    RiskAssessmentType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
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


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"detail-{uuid.uuid4()}@example.com",
        display_name="Risk Detail Reader",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"X-User-Id": str(user.id)}


def _create_risk_record(
    db_session: Session,
    *,
    created_by_user_id: uuid.UUID | None = None,
    owner_user_id: uuid.UUID | None = None,
    board_of_origin_id: uuid.UUID | None = None,
) -> RiskRecord:
    risk_record = RiskRecord(
        risk_id=f"RISK-2026-{uuid.uuid4().int % 9999:04d}",
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
        created_by_user_id=created_by_user_id,
        owner_user_id=owner_user_id,
        board_of_origin_id=board_of_origin_id,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


def _create_committee(
    db_session: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_fixed: bool = False,
) -> Committee:
    committee = Committee(
        name=f"Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=is_fixed,
        is_active=True,
    )
    db_session.add(committee)
    db_session.commit()
    db_session.refresh(committee)
    return committee


def _create_membership(
    db_session: Session,
    *,
    committee_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    db_session.add(CommitteeMember(committee_id=committee_id, user_id=user_id))
    db_session.commit()


def _seed_detail_data(db_session: Session, risk_record: RiskRecord) -> None:
    now = datetime.now(timezone.utc)
    committee = _create_committee(db_session)
    db_session.add_all(
        [
            RiskAssessment(
                risk_record_id=risk_record.id,
                assessment_type=RiskAssessmentType.INITIAL,
                severity="Major",
                likelihood="Remote",
                risk_level="Medium",
                assessed_at=now,
            ),
            RiskAction(
                risk_record_id=risk_record.id,
                title="Mitigation action",
                status=RiskActionStatus.OPEN,
            ),
            RiskDecision(
                risk_record_id=risk_record.id,
                committee_id=committee.id,
                decision_type=RiskDecisionType.APPROVE,
                decision_text="Approved.",
                decided_at=now,
            ),
            AuditLog(
                entity_type="RiskRecord",
                entity_id=risk_record.id,
                action=AuditAction.CREATE,
                changed_at=now,
            ),
        ]
    )
    db_session.commit()


def test_get_risk_detail_returns_200(client: TestClient, db_session: Session) -> None:
    creator = _create_user(db_session)
    risk_record = _create_risk_record(db_session, created_by_user_id=creator.id)

    response = client.get(f"/risks/{risk_record.id}/detail", headers=_headers(creator))

    assert response.status_code == 200


def test_get_risk_detail_response_includes_aggregate_sections(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    risk_record = _create_risk_record(db_session, created_by_user_id=creator.id)
    _seed_detail_data(db_session, risk_record)

    response = client.get(f"/risks/{risk_record.id}/detail", headers=_headers(creator))

    assert response.status_code == 200
    body = response.json()
    assert body["risk_record"]["id"] == str(risk_record.id)
    assert isinstance(body["assessments"], list)
    assert isinstance(body["actions"], list)
    assert isinstance(body["decisions"], list)
    assert body["audit_summary"]["total_count"] == 1


def test_get_unknown_risk_detail_returns_404(
    client: TestClient, db_session: Session
) -> None:
    response = client.get(
        f"/risks/{uuid.uuid4()}/detail", headers=_headers(_create_user(db_session))
    )

    assert response.status_code == 404


def test_get_risk_record_still_works_with_detail_route(
    client: TestClient,
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = client.get(f"/risks/{risk_record.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(risk_record.id)


@pytest.mark.parametrize("reader_state", ["missing", "unknown", "inactive"])
def test_detail_reader_authentication_errors(
    client: TestClient,
    db_session: Session,
    reader_state: str,
) -> None:
    creator = _create_user(db_session)
    risk_record = _create_risk_record(db_session, created_by_user_id=creator.id)
    headers: dict[str, str] | None = None
    expected_status = 400
    if reader_state == "unknown":
        headers = {"X-User-Id": str(uuid.uuid4())}
        expected_status = 401
    elif reader_state == "inactive":
        headers = _headers(_create_user(db_session, is_active=False))
        expected_status = 403

    response = client.get(f"/risks/{risk_record.id}/detail", headers=headers)

    assert response.status_code == expected_status


@pytest.mark.parametrize("governance_level", [AuthorityLevel.MIDDLE, AuthorityLevel.HIGH])
def test_detail_allows_related_users_and_fixed_governance_member(
    client: TestClient,
    db_session: Session,
    governance_level: AuthorityLevel,
) -> None:
    now = datetime.now(timezone.utc)
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    board_member = _create_user(db_session)
    assessment_actor = _create_user(db_session)
    action_owner = _create_user(db_session)
    decision_maker = _create_user(db_session)
    decision_member = _create_user(db_session)
    governance_member = _create_user(db_session)
    board = _create_committee(db_session)
    decision_committee = _create_committee(db_session)
    governance_committee = _create_committee(
        db_session, authority_level=governance_level, is_fixed=True
    )
    risk_record = _create_risk_record(
        db_session,
        created_by_user_id=creator.id,
        owner_user_id=owner.id,
        board_of_origin_id=board.id,
    )
    _create_membership(db_session, committee_id=board.id, user_id=board_member.id)
    _create_membership(
        db_session, committee_id=decision_committee.id, user_id=decision_member.id
    )
    _create_membership(
        db_session, committee_id=governance_committee.id, user_id=governance_member.id
    )
    db_session.add_all(
        [
            RiskAssessment(
                risk_record_id=risk_record.id,
                assessment_type=RiskAssessmentType.INITIAL,
                severity="Major",
                likelihood="Remote",
                risk_level="Medium",
                assessed_at=now,
                assessed_by_user_id=assessment_actor.id,
            ),
            RiskAction(
                risk_record_id=risk_record.id,
                title="Mitigation action",
                status=RiskActionStatus.OPEN,
                action_owner_user_id=action_owner.id,
            ),
            RiskDecision(
                risk_record_id=risk_record.id,
                committee_id=decision_committee.id,
                decision_type=RiskDecisionType.APPROVE,
                decision_text="Approved.",
                decided_at=now,
                decided_by_user_id=decision_maker.id,
            ),
        ]
    )
    db_session.commit()

    for user in (
        creator,
        owner,
        board_member,
        assessment_actor,
        action_owner,
        decision_maker,
        decision_member,
        governance_member,
    ):
        assert client.get(
            f"/risks/{risk_record.id}/detail", headers=_headers(user)
        ).status_code == 200


def test_unrelated_active_user_cannot_read_detail(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    unrelated_user = _create_user(db_session)
    risk_record = _create_risk_record(db_session, created_by_user_id=creator.id)

    response = client.get(
        f"/risks/{risk_record.id}/detail", headers=_headers(unrelated_user)
    )

    assert response.status_code == 400
