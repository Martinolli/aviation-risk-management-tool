import uuid
from datetime import datetime, timezone

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
    RiskActionStatus,
    RiskAssessmentType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.models.user import User
from app.services.risk_detail_service import (
    RiskDetailBusinessRuleError,
    get_risk_record_detail,
)
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    validate_active_user,
)
from app.services.risk_service import list_authorized_risk_records


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


def _create_user(db: Session, email: str) -> User:
    user = User(email=email, display_name=email, is_active=True)
    db.add(user)
    db.flush()
    return user


def _create_committee(
    db: Session,
    *,
    name: str,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_fixed: bool = False,
    is_active: bool = True,
) -> Committee:
    committee = Committee(
        name=name,
        authority_level=authority_level,
        committee_type=(
            CommitteeType.RISK_MANAGEMENT_COMMITTEE
            if authority_level == AuthorityLevel.MIDDLE
            else CommitteeType.OPERATIONAL_BOARD
        ),
        is_fixed=is_fixed,
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
) -> None:
    db.add(
        CommitteeMember(
            committee_id=committee.id,
            user_id=user.id,
            role_label=role_label,
            is_active=is_active,
        )
    )
    db.flush()


def _create_risk(
    db: Session,
    *,
    board_of_origin_id: uuid.UUID | None,
    domain: RiskDomain,
    created_by_user_id: uuid.UUID | None = None,
    owner_user_id: uuid.UUID | None = None,
) -> RiskRecord:
    risk = RiskRecord(
        problem_description=f"{domain.value} risk",
        domain=domain,
        board_of_origin_id=board_of_origin_id,
        created_by_user_id=created_by_user_id,
        owner_user_id=owner_user_id,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db.add(risk)
    db.flush()
    return risk


def test_board_member_list_and_detail_access_match(db_session: Session) -> None:
    gulzar = _create_user(db_session, "gulzar.hussain@calidus.ae")
    industrial = _create_committee(db_session, name="Industrial Safety Committee")
    aircraft = _create_committee(db_session, name="Aircraft Safety Committee")
    _add_membership(db_session, committee=industrial, user=gulzar)
    industrial_risk = _create_risk(
        db_session,
        board_of_origin_id=industrial.id,
        domain=RiskDomain.QUALITY,
    )
    aircraft_risk = _create_risk(
        db_session,
        board_of_origin_id=aircraft.id,
        domain=RiskDomain.ENGINEERING,
    )

    readable_ids = {
        risk.id
        for risk in list_authorized_risk_records(
            db_session,
            requested_by_user_id=gulzar.id,
        )
    }

    assert industrial_risk.id in readable_ids
    assert aircraft_risk.id not in readable_ids
    assert get_risk_record_detail(
        db_session,
        risk_record_id=industrial_risk.id,
        requested_by_user_id=gulzar.id,
    ) is not None
    with pytest.raises(RiskDetailBusinessRuleError, match="not authorized"):
        get_risk_record_detail(
            db_session,
            risk_record_id=aircraft_risk.id,
            requested_by_user_id=gulzar.id,
        )


def test_other_low_board_member_cannot_read_industrial_risk(
    db_session: Session,
) -> None:
    kevin = _create_user(db_session, "kevin.rooney@calidus.ae")
    industrial = _create_committee(db_session, name="Industrial Safety Committee")
    aircraft = _create_committee(db_session, name="Aircraft Safety Committee")
    _add_membership(db_session, committee=aircraft, user=kevin)
    industrial_risk = _create_risk(
        db_session,
        board_of_origin_id=industrial.id,
        domain=RiskDomain.QUALITY,
    )

    assert industrial_risk not in list_authorized_risk_records(
        db_session,
        requested_by_user_id=kevin.id,
    )
    with pytest.raises(RiskDetailBusinessRuleError, match="not authorized"):
        get_risk_record_detail(
            db_session,
            risk_record_id=industrial_risk.id,
            requested_by_user_id=kevin.id,
        )


def test_fixed_governance_member_can_read_board_and_boardless_risks(
    db_session: Session,
) -> None:
    joao = _create_user(db_session, "joao.bosco@calidus.ae")
    industrial = _create_committee(db_session, name="Industrial Safety Committee")
    rmc = _create_committee(
        db_session,
        name="Risk Management Committee",
        authority_level=AuthorityLevel.MIDDLE,
        is_fixed=True,
    )
    _add_membership(
        db_session,
        committee=rmc,
        user=joao,
        role_label="Governance Administrator",
    )
    industrial_risk = _create_risk(
        db_session,
        board_of_origin_id=industrial.id,
        domain=RiskDomain.QUALITY,
    )
    boardless_risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
    )

    assert {
        risk.id
        for risk in list_authorized_risk_records(
            db_session,
            requested_by_user_id=joao.id,
        )
    } == {industrial_risk.id, boardless_risk.id}
    for risk in (industrial_risk, boardless_risk):
        assert get_risk_record_detail(
            db_session,
            risk_record_id=risk.id,
            requested_by_user_id=joao.id,
        ) is not None


def test_boardless_risk_is_hidden_from_uninvolved_low_member(
    db_session: Session,
) -> None:
    low_member = _create_user(db_session, "low.member@example.com")
    board = _create_committee(db_session, name="Operational Board")
    _add_membership(db_session, committee=board, user=low_member)
    boardless_risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
    )

    assert list_authorized_risk_records(
        db_session,
        requested_by_user_id=low_member.id,
    ) == []
    with pytest.raises(RiskDetailBusinessRuleError, match="not authorized"):
        get_risk_record_detail(
            db_session,
            risk_record_id=boardless_risk.id,
            requested_by_user_id=low_member.id,
        )


def test_system_admin_label_alone_does_not_grant_governance_read(
    db_session: Session,
) -> None:
    system_admin = _create_user(db_session, "system.admin@example.com")
    risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
    )

    assert risk not in list_authorized_risk_records(
        db_session,
        requested_by_user_id=system_admin.id,
    )


def test_creator_and_owner_can_read_without_committee_membership(
    db_session: Session,
) -> None:
    creator = _create_user(db_session, "creator@example.com")
    owner = _create_user(db_session, "owner@example.com")
    risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
        created_by_user_id=creator.id,
        owner_user_id=owner.id,
    )

    assert can_read_risk_record(db_session, risk_record=risk, user_id=creator.id)
    assert can_read_risk_record(db_session, risk_record=risk, user_id=owner.id)


def test_assessor_action_owner_and_decision_maker_can_read_related_risk(
    db_session: Session,
) -> None:
    assessor = _create_user(db_session, "assessor@example.com")
    action_owner = _create_user(db_session, "action.owner@example.com")
    decision_maker = _create_user(db_session, "decision.maker@example.com")
    committee = _create_committee(db_session, name="Decision Committee")
    risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
    )
    db_session.add_all(
        [
            RiskAssessment(
                risk_record_id=risk.id,
                assessment_type=RiskAssessmentType.INITIAL,
                severity="Major",
                likelihood="Remote",
                risk_level="Medium",
                assessed_by_user_id=assessor.id,
                assessed_at=datetime.now(timezone.utc),
            ),
            RiskAction(
                risk_record_id=risk.id,
                title="Mitigation",
                status=RiskActionStatus.OPEN,
                action_owner_user_id=action_owner.id,
            ),
            RiskDecision(
                risk_record_id=risk.id,
                committee_id=committee.id,
                decision_type=RiskDecisionType.APPROVE,
                decision_text="Approved",
                decided_by_user_id=decision_maker.id,
                decided_at=datetime.now(timezone.utc),
            ),
        ]
    )
    db_session.flush()

    for user in (assessor, action_owner, decision_maker):
        assert can_read_risk_record(db_session, risk_record=risk, user_id=user.id)


def test_member_of_decision_committee_can_read_after_committee_decision(
    db_session: Session,
) -> None:
    member = _create_user(db_session, "decision.member@example.com")
    committee = _create_committee(db_session, name="Decision History Committee")
    _add_membership(db_session, committee=committee, user=member)
    risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
    )

    assert not can_read_risk_record(db_session, risk_record=risk, user_id=member.id)
    db_session.add(
        RiskDecision(
            risk_record_id=risk.id,
            committee_id=committee.id,
            decision_type=RiskDecisionType.APPROVE,
            decision_text="Approved",
            decided_at=datetime.now(timezone.utc),
        )
    )
    db_session.flush()

    assert can_read_risk_record(db_session, risk_record=risk, user_id=member.id)


def test_validate_active_user_rejects_inactive_user(db_session: Session) -> None:
    inactive_user = _create_user(db_session, "inactive@example.com")
    inactive_user.is_active = False
    db_session.flush()

    with pytest.raises(RiskAccessBusinessRuleError, match="user is inactive"):
        validate_active_user(
            db_session,
            user_id=inactive_user.id,
            context="Risk access",
        )


@pytest.mark.parametrize("inactive_target", ["membership", "committee"])
def test_inactive_committee_or_membership_does_not_grant_access(
    db_session: Session,
    inactive_target: str,
) -> None:
    user = _create_user(db_session, f"inactive.{inactive_target}@example.com")
    committee = _create_committee(
        db_session,
        name=f"Inactive {inactive_target} Committee",
        is_active=inactive_target != "committee",
    )
    _add_membership(
        db_session,
        committee=committee,
        user=user,
        is_active=inactive_target != "membership",
    )
    risk = _create_risk(
        db_session,
        board_of_origin_id=committee.id,
        domain=RiskDomain.QUALITY,
    )

    assert not can_read_risk_record(db_session, risk_record=risk, user_id=user.id)


def test_high_fixed_governance_member_can_read_risk(db_session: Session) -> None:
    member = _create_user(db_session, "high.member@example.com")
    high_committee = _create_committee(
        db_session,
        name="Executive Safety Management Committee",
        authority_level=AuthorityLevel.HIGH,
        is_fixed=True,
    )
    _add_membership(db_session, committee=high_committee, user=member)
    risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
    )

    assert can_read_risk_record(db_session, risk_record=risk, user_id=member.id)


def test_non_fixed_middle_membership_does_not_grant_governance_access(
    db_session: Session,
) -> None:
    member = _create_user(db_session, "nonfixed.middle@example.com")
    committee = _create_committee(
        db_session,
        name="Temporary Middle Committee",
        authority_level=AuthorityLevel.MIDDLE,
        is_fixed=False,
    )
    _add_membership(db_session, committee=committee, user=member)
    risk = _create_risk(
        db_session,
        board_of_origin_id=None,
        domain=RiskDomain.OTHER,
    )

    assert not can_read_risk_record(db_session, risk_record=risk, user_id=member.id)


def test_low_board_member_reads_only_board_of_origin_risks(
    db_session: Session,
) -> None:
    member = _create_user(db_session, "industrial.member@example.com")
    industrial = _create_committee(db_session, name="Industrial Board")
    flight_test = _create_committee(db_session, name="Flight Test Board")
    _add_membership(db_session, committee=industrial, user=member)
    industrial_risk = _create_risk(
        db_session,
        board_of_origin_id=industrial.id,
        domain=RiskDomain.QUALITY,
    )
    flight_test_risk = _create_risk(
        db_session,
        board_of_origin_id=flight_test.id,
        domain=RiskDomain.FLIGHT_TEST,
    )

    assert can_read_risk_record(
        db_session, risk_record=industrial_risk, user_id=member.id
    )
    assert not can_read_risk_record(
        db_session, risk_record=flight_test_risk, user_id=member.id
    )
