import uuid
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
from app.models.enums import (
    AuthorityLevel,
    CommitteeType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskRecord
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
        email=f"{uuid.uuid4()}@example.com",
        display_name="Queue API User",
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id=user.id)}"}


def _create_committee(
    db: Session,
    *,
    name: str,
    authority_level: AuthorityLevel,
) -> Committee:
    committee = Committee(
        name=name,
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
    db.commit()
    db.refresh(committee)
    return committee


def _add_membership(
    db: Session,
    *,
    committee: Committee,
    user: User,
    role_label: str,
) -> None:
    db.add(
        CommitteeMember(
            committee_id=committee.id,
            user_id=user.id,
            role_label=role_label,
            is_active=True,
        )
    )
    db.commit()


def _create_risk(
    db: Session,
    *,
    workflow_status: RiskWorkflowStatus,
    board: Committee | None = None,
    domain: RiskDomain = RiskDomain.OTHER,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=f"RISK-{uuid.uuid4().hex[:8]}",
        problem_description="Decision queue API risk",
        domain=domain,
        board_of_origin_id=board.id if board else None,
        workflow_status=workflow_status,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


def test_get_my_decision_queue_requires_authenticated_active_user(
    client: TestClient,
    db_session: Session,
) -> None:
    inactive_user = _create_user(db_session, is_active=False)

    unauthenticated = client.get("/decision-queue/my")
    inactive = client.get(
        "/decision-queue/my", headers=_auth_headers(inactive_user)
    )

    assert unauthenticated.status_code == 400
    assert "authenticated active user" in unauthenticated.json()["error"]["message"]
    assert inactive.status_code == 403


def test_low_member_receives_only_their_committee_and_queue_items(
    client: TestClient,
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    industrial = _create_committee(
        db_session,
        name=INDUSTRIAL_COMMITTEE,
        authority_level=AuthorityLevel.LOW,
    )
    other_board = _create_committee(
        db_session,
        name="Other Operational Board",
        authority_level=AuthorityLevel.LOW,
    )
    _add_membership(
        db_session,
        committee=industrial,
        user=member,
        role_label="Committee Member",
    )
    expected_risk = _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        board=industrial,
        domain=RiskDomain.QUALITY,
    )
    _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        board=other_board,
        domain=RiskDomain.FLIGHT_TEST,
    )

    response = client.get("/decision-queue/my", headers=_auth_headers(member))

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(member.id)
    assert len(body["committees"]) == 1
    committee = body["committees"][0]
    assert committee["committee_id"] == str(industrial.id)
    assert committee["authority_level"] == "LOW"
    assert committee["role_label"] == "Committee Member"
    assert committee["queue_scope"] == [
        "QUALITY",
        "MANUFACTURING",
        "PRODUCTION",
        "SUPPLY_CHAIN",
        "OHSE",
        "MAINTENANCE",
        "SUPPLIER_INTERFACE",
    ]
    assert [item["risk_record"]["id"] for item in body["queue_items"]] == [
        str(expected_risk.id)
    ]


def test_governance_administrator_receives_rmc_queue(
    client: TestClient,
    db_session: Session,
) -> None:
    governance_admin = _create_user(db_session)
    rmc = _create_committee(
        db_session,
        name="Risk Management Committee",
        authority_level=AuthorityLevel.MIDDLE,
    )
    _add_membership(
        db_session,
        committee=rmc,
        user=governance_admin,
        role_label="Governance Administrator",
    )
    risk = _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    )

    response = client.get(
        "/decision-queue/my", headers=_auth_headers(governance_admin)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["committees"][0]["committee_name"] == "Risk Management Committee"
    assert body["committees"][0]["authority_level"] == "MIDDLE"
    assert body["committees"][0]["role_label"] == "Governance Administrator"
    assert body["committees"][0]["queue_scope"] == "Escalated RMC risks"
    assert body["queue_items"][0]["risk_record"]["id"] == str(risk.id)


def test_user_without_active_memberships_receives_empty_queue(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)

    response = client.get("/decision-queue/my", headers=_auth_headers(user))

    assert response.status_code == 200
    assert response.json() == {
        "user_id": str(user.id),
        "committees": [],
        "queue_items": [],
    }
