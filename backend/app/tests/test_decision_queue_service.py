import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
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
from app.services.decision_queue_service import (
    AIRCRAFT_COMMITTEE,
    FLIGHT_TEST_COMMITTEE,
    INDUSTRIAL_COMMITTEE,
    DecisionQueueBusinessRuleError,
    get_my_decision_queue,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session
    Base.metadata.drop_all(engine)


def _create_user(
    db: Session,
    email: str | None = None,
    *,
    is_active: bool = True,
) -> User:
    user = User(
        email=email or f"{uuid.uuid4()}@example.com",
        display_name="Queue User",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _create_committee(
    db: Session,
    *,
    name: str,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_fixed: bool | None = None,
    is_active: bool = True,
) -> Committee:
    committee_type = {
        AuthorityLevel.LOW: CommitteeType.OPERATIONAL_BOARD,
        AuthorityLevel.MIDDLE: CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        AuthorityLevel.HIGH: CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
    }[authority_level]
    committee = Committee(
        name=name,
        authority_level=authority_level,
        committee_type=committee_type,
        is_fixed=(authority_level != AuthorityLevel.LOW if is_fixed is None else is_fixed),
        is_active=is_active,
    )
    db.add(committee)
    db.flush()
    return committee


def _add_membership(
    db: Session,
    *,
    committee: Committee,
    user: User,
    role_label: str = "Committee Member",
    is_active: bool = True,
) -> CommitteeMember:
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        role_label=role_label,
        is_active=is_active,
    )
    db.add(membership)
    db.flush()
    return membership


def _create_risk(
    db: Session,
    *,
    board: Committee | None = None,
    domain: RiskDomain = RiskDomain.OTHER,
    workflow_status: RiskWorkflowStatus,
    is_active: bool = True,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=f"RISK-{uuid.uuid4().hex[:8]}",
        problem_description=f"{domain.value} queue risk",
        domain=domain,
        board_of_origin_id=board.id if board else None,
        workflow_status=workflow_status,
        lifecycle_status=(
            RiskLifecycleStatus.CLOSED
            if workflow_status == RiskWorkflowStatus.CLOSED
            else RiskLifecycleStatus.OPEN
        ),
        is_active=is_active,
    )
    db.add(risk)
    db.flush()
    return risk


def test_low_industrial_member_sees_only_industrial_decision_risk(
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    industrial = _create_committee(db_session, name=INDUSTRIAL_COMMITTEE)
    flight_test = _create_committee(db_session, name=FLIGHT_TEST_COMMITTEE)
    _add_membership(db_session, committee=industrial, user=member)
    industrial_risk = _create_risk(
        db_session,
        board=industrial,
        domain=RiskDomain.QUALITY,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
    )
    _create_risk(
        db_session,
        board=flight_test,
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
    )

    queue = get_my_decision_queue(db_session, requested_by_user_id=member.id)

    assert [committee.committee_id for committee in queue.committees] == [industrial.id]
    assert queue.committees[0].queue_scope == [
        "QUALITY",
        "MANUFACTURING",
        "PRODUCTION",
        "SUPPLY_CHAIN",
        "OHSE",
        "MAINTENANCE",
        "SUPPLIER_INTERFACE",
    ]
    assert [item.risk_record.id for item in queue.queue_items] == [industrial_risk.id]


@pytest.mark.parametrize(
    ("committee_name", "domain", "expected_scope"),
    [
        (FLIGHT_TEST_COMMITTEE, RiskDomain.FLIGHT_TEST, ["FLIGHT_TEST"]),
        (
            AIRCRAFT_COMMITTEE,
            RiskDomain.ENGINEERING,
            ["ENGINEERING", "CONTINUED_AIRWORTHINESS"],
        ),
    ],
)
def test_low_member_sees_risk_waiting_for_their_board(
    db_session: Session,
    committee_name: str,
    domain: RiskDomain,
    expected_scope: list[str],
) -> None:
    member = _create_user(db_session)
    committee = _create_committee(db_session, name=committee_name)
    _add_membership(db_session, committee=committee, user=member)
    risk = _create_risk(
        db_session,
        board=committee,
        domain=domain,
        workflow_status=RiskWorkflowStatus.UNDER_OPERATIONAL_BOARD_REVIEW,
    )

    queue = get_my_decision_queue(db_session, requested_by_user_id=member.id)

    assert queue.committees[0].queue_scope == expected_scope
    assert [item.risk_record.id for item in queue.queue_items] == [risk.id]


def test_rmc_governance_administrator_sees_only_escalated_rmc_risks(
    db_session: Session,
) -> None:
    governance_admin = _create_user(db_session, "joao.bosco@calidus.ae")
    rmc = _create_committee(
        db_session,
        name="Risk Management Committee",
        authority_level=AuthorityLevel.MIDDLE,
    )
    low_board = _create_committee(db_session, name=INDUSTRIAL_COMMITTEE)
    _add_membership(
        db_session,
        committee=rmc,
        user=governance_admin,
        role_label="Governance Administrator",
    )
    escalated = _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    )
    _create_risk(
        db_session,
        board=low_board,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
    )

    queue = get_my_decision_queue(
        db_session, requested_by_user_id=governance_admin.id
    )

    assert queue.committees[0].committee_id == rmc.id
    assert queue.committees[0].role_label == "Governance Administrator"
    assert queue.committees[0].queue_scope == "Escalated RMC risks"
    assert [item.risk_record.id for item in queue.queue_items] == [escalated.id]


def test_high_member_sees_executive_escalated_risk(db_session: Session) -> None:
    member = _create_user(db_session)
    executive = _create_committee(
        db_session,
        name="Executive Safety Management Committee",
        authority_level=AuthorityLevel.HIGH,
    )
    _add_membership(db_session, committee=executive, user=member)
    escalated = _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
    )
    _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    )

    queue = get_my_decision_queue(db_session, requested_by_user_id=member.id)

    assert queue.committees[0].queue_scope == "Escalated executive risks"
    assert [item.risk_record.id for item in queue.queue_items] == [escalated.id]


@pytest.mark.parametrize(
    "workflow_status",
    [
        RiskWorkflowStatus.DRAFT,
        RiskWorkflowStatus.CLOSED,
        RiskWorkflowStatus.RETURNED_FOR_REVISION,
        RiskWorkflowStatus.ACCEPTED,
        RiskWorkflowStatus.REJECTED,
    ],
)
def test_terminal_or_non_queue_workflow_statuses_are_excluded(
    db_session: Session,
    workflow_status: RiskWorkflowStatus,
) -> None:
    member = _create_user(db_session)
    board = _create_committee(db_session, name="Status Exclusion Board")
    _add_membership(db_session, committee=board, user=member)
    _create_risk(
        db_session,
        board=board,
        workflow_status=workflow_status,
    )

    queue = get_my_decision_queue(db_session, requested_by_user_id=member.id)

    assert queue.queue_items == []


def test_inactive_risk_is_excluded(db_session: Session) -> None:
    member = _create_user(db_session)
    board = _create_committee(db_session, name="Inactive Risk Board")
    _add_membership(db_session, committee=board, user=member)
    _create_risk(
        db_session,
        board=board,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        is_active=False,
    )

    assert get_my_decision_queue(
        db_session, requested_by_user_id=member.id
    ).queue_items == []


@pytest.mark.parametrize("inactive_target", ["membership", "committee"])
def test_inactive_membership_or_committee_gives_no_queue(
    db_session: Session,
    inactive_target: str,
) -> None:
    member = _create_user(db_session)
    board = _create_committee(
        db_session,
        name=f"Inactive {inactive_target} Board",
        is_active=inactive_target != "committee",
    )
    _add_membership(
        db_session,
        committee=board,
        user=member,
        is_active=inactive_target != "membership",
    )
    _create_risk(
        db_session,
        board=board,
        workflow_status=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
    )

    queue = get_my_decision_queue(db_session, requested_by_user_id=member.id)

    assert queue.committees == []
    assert queue.queue_items == []


def test_unauthenticated_unknown_and_inactive_users_are_rejected(
    db_session: Session,
) -> None:
    inactive_user = _create_user(db_session, is_active=False)

    for user_id, message in [
        (None, "authenticated active user"),
        (uuid.uuid4(), "user does not exist"),
        (inactive_user.id, "user is inactive"),
    ]:
        with pytest.raises(DecisionQueueBusinessRuleError, match=message):
            get_my_decision_queue(db_session, requested_by_user_id=user_id)


def test_system_admin_without_committee_membership_has_no_governance_queue(
    db_session: Session,
) -> None:
    system_admin = _create_user(db_session, "system.admin@example.com")
    _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    )

    queue = get_my_decision_queue(
        db_session, requested_by_user_id=system_admin.id
    )

    assert queue.committees == []
    assert queue.queue_items == []


def test_non_fixed_middle_membership_is_not_a_governance_decision_queue(
    db_session: Session,
) -> None:
    member = _create_user(db_session)
    non_fixed_middle = _create_committee(
        db_session,
        name="Temporary Middle Committee",
        authority_level=AuthorityLevel.MIDDLE,
        is_fixed=False,
    )
    _add_membership(db_session, committee=non_fixed_middle, user=member)
    _create_risk(
        db_session,
        workflow_status=RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    )

    queue = get_my_decision_queue(db_session, requested_by_user_id=member.id)

    assert queue.committees == []
    assert queue.queue_items == []
