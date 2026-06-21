import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
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
from app.services.risk_detail_service import (
    RiskDetailBusinessRuleError,
    get_risk_record_detail,
)


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"user-{uuid.uuid4()}@example.com",
        display_name="Risk Detail User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_risk_record(
    db_session: Session,
    *,
    is_active: bool = True,
    created_by_user_id: uuid.UUID | None = None,
    owner_user_id: uuid.UUID | None = None,
    board_of_origin_id: uuid.UUID | None = None,
) -> RiskRecord:
    if created_by_user_id is None and owner_user_id is None:
        created_by_user_id = _create_user(db_session).id
    risk_record = RiskRecord(
        risk_id=f"RISK-2026-{uuid.uuid4().int % 9999:04d}",
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=is_active,
        created_by_user_id=created_by_user_id,
        owner_user_id=owner_user_id,
        board_of_origin_id=board_of_origin_id,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


def _create_committee(
    db_session: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_fixed: bool = False,
    is_active: bool = True,
) -> Committee:
    committee = Committee(
        name=f"Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=is_fixed,
        is_active=is_active,
    )
    db_session.add(committee)
    db_session.flush()
    return committee


def _create_committee_membership(
    db_session: Session,
    *,
    committee_id: uuid.UUID,
    user_id: uuid.UUID,
    is_active: bool = True,
) -> CommitteeMember:
    membership = CommitteeMember(
        committee_id=committee_id,
        user_id=user_id,
        is_active=is_active,
    )
    db_session.add(membership)
    db_session.flush()
    return membership


def _set_created_at(db_session: Session, model, created_at: datetime) -> None:
    model.created_at = created_at
    model.updated_at = created_at
    db_session.flush()


def _create_assessment(
    db_session: Session,
    risk_record_id: uuid.UUID,
    created_at: datetime,
    assessment_type: RiskAssessmentType = RiskAssessmentType.INITIAL,
    assessed_by_user_id: uuid.UUID | None = None,
) -> RiskAssessment:
    assessment = RiskAssessment(
        risk_record_id=risk_record_id,
        assessment_type=assessment_type,
        severity="Major",
        likelihood="Remote",
        risk_level="Medium",
        assessed_at=created_at,
        assessed_by_user_id=assessed_by_user_id,
    )
    db_session.add(assessment)
    db_session.flush()
    _set_created_at(db_session, assessment, created_at)
    return assessment


def _create_action(
    db_session: Session,
    risk_record_id: uuid.UUID,
    created_at: datetime,
    action_owner_user_id: uuid.UUID | None = None,
) -> RiskAction:
    action = RiskAction(
        risk_record_id=risk_record_id,
        title=f"Action {uuid.uuid4()}",
        status=RiskActionStatus.OPEN,
        action_owner_user_id=action_owner_user_id,
    )
    db_session.add(action)
    db_session.flush()
    _set_created_at(db_session, action, created_at)
    return action


def _create_decision(
    db_session: Session,
    risk_record_id: uuid.UUID,
    committee_id: uuid.UUID,
    decided_at: datetime,
    decided_by_user_id: uuid.UUID | None = None,
) -> RiskDecision:
    decision = RiskDecision(
        risk_record_id=risk_record_id,
        committee_id=committee_id,
        decision_type=RiskDecisionType.APPROVE,
        decision_text="Approved.",
        decided_at=decided_at,
        decided_by_user_id=decided_by_user_id,
    )
    db_session.add(decision)
    db_session.flush()
    _set_created_at(db_session, decision, decided_at)
    return decision


def _create_audit_log(
    db_session: Session,
    risk_record_id: uuid.UUID,
    action: AuditAction,
    changed_at: datetime,
) -> AuditLog:
    audit_log = AuditLog(
        entity_type="RiskRecord",
        entity_id=risk_record_id,
        action=action,
        field_name=None,
        old_value=None,
        new_value=None,
        changed_at=changed_at,
    )
    db_session.add(audit_log)
    db_session.flush()
    return audit_log


def test_get_risk_record_detail_returns_risk_record(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)

    detail = get_risk_record_detail(
        db_session,
        risk_record_id=risk_record.id,
        requested_by_user_id=risk_record.created_by_user_id,
    )

    assert detail["risk_record"] is risk_record


def test_detail_includes_related_resources_for_the_risk(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    assessment = _create_assessment(db_session, risk_record.id, now)
    action = _create_action(db_session, risk_record.id, now)
    decision = _create_decision(db_session, risk_record.id, committee.id, now)

    detail = get_risk_record_detail(
        db_session,
        risk_record_id=risk_record.id,
        requested_by_user_id=risk_record.created_by_user_id,
    )

    assert detail["assessments"] == [assessment]
    assert detail["actions"] == [action]
    assert detail["decisions"] == [decision]


def test_detail_excludes_related_resources_from_other_risks(
    db_session: Session,
) -> None:
    now = datetime.now(timezone.utc)
    target_risk = _create_risk_record(db_session)
    other_risk = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    target_assessment = _create_assessment(db_session, target_risk.id, now)
    target_action = _create_action(db_session, target_risk.id, now)
    target_decision = _create_decision(db_session, target_risk.id, committee.id, now)
    _create_assessment(db_session, other_risk.id, now + timedelta(minutes=1))
    _create_action(db_session, other_risk.id, now + timedelta(minutes=1))
    _create_decision(
        db_session,
        other_risk.id,
        committee.id,
        now + timedelta(minutes=1),
    )

    detail = get_risk_record_detail(
        db_session,
        risk_record_id=target_risk.id,
        requested_by_user_id=target_risk.created_by_user_id,
    )

    assert detail["assessments"] == [target_assessment]
    assert detail["actions"] == [target_action]
    assert detail["decisions"] == [target_decision]


def test_detail_orders_related_resources_descending(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    older_assessment = _create_assessment(db_session, risk_record.id, now)
    newer_assessment = _create_assessment(
        db_session,
        risk_record.id,
        now + timedelta(minutes=1),
        assessment_type=RiskAssessmentType.RESIDUAL,
    )
    older_action = _create_action(db_session, risk_record.id, now)
    newer_action = _create_action(
        db_session,
        risk_record.id,
        now + timedelta(minutes=1),
    )
    older_decision = _create_decision(db_session, risk_record.id, committee.id, now)
    newer_decision = _create_decision(
        db_session,
        risk_record.id,
        committee.id,
        now + timedelta(minutes=1),
    )

    detail = get_risk_record_detail(
        db_session,
        risk_record_id=risk_record.id,
        requested_by_user_id=risk_record.created_by_user_id,
    )

    assert detail["assessments"] == [newer_assessment, older_assessment]
    assert detail["actions"] == [newer_action, older_action]
    assert detail["decisions"] == [newer_decision, older_decision]


def test_audit_summary_counts_and_latest_changed_at(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    risk_record = _create_risk_record(db_session)
    _create_audit_log(db_session, risk_record.id, AuditAction.CREATE, now)
    _create_audit_log(
        db_session,
        risk_record.id,
        AuditAction.UPDATE,
        now + timedelta(minutes=1),
    )
    _create_audit_log(
        db_session,
        risk_record.id,
        AuditAction.SUBMIT,
        now + timedelta(minutes=2),
    )
    _create_audit_log(
        db_session,
        risk_record.id,
        AuditAction.APPROVE,
        now + timedelta(minutes=3),
    )
    other_risk = _create_risk_record(db_session)
    _create_audit_log(
        db_session,
        other_risk.id,
        AuditAction.UPDATE,
        now + timedelta(minutes=4),
    )

    detail = get_risk_record_detail(
        db_session,
        risk_record_id=risk_record.id,
        requested_by_user_id=risk_record.created_by_user_id,
    )
    summary = detail["audit_summary"]

    assert summary["total_count"] == 4
    assert summary["create_count"] == 1
    assert summary["update_count"] == 1
    assert summary["workflow_count"] == 2
    assert summary["latest_changed_at"].replace(tzinfo=timezone.utc) == (
        now + timedelta(minutes=3)
    )


def test_archived_inactive_risk_can_still_be_retrieved(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session, is_active=False)

    detail = get_risk_record_detail(
        db_session,
        risk_record_id=risk_record.id,
        requested_by_user_id=risk_record.created_by_user_id,
    )

    assert detail["risk_record"] is risk_record


def test_unknown_risk_returns_none_for_valid_reader(db_session: Session) -> None:
    user = _create_user(db_session)

    assert get_risk_record_detail(
        db_session,
        risk_record_id=uuid.uuid4(),
        requested_by_user_id=user.id,
    ) is None


@pytest.mark.parametrize("reader_kind", ["missing", "unknown", "inactive"])
def test_detail_requires_an_authenticated_active_reader(
    db_session: Session,
    reader_kind: str,
) -> None:
    risk_record = _create_risk_record(db_session)
    user_id: uuid.UUID | None
    if reader_kind == "missing":
        user_id = None
    elif reader_kind == "unknown":
        user_id = uuid.uuid4()
    else:
        user_id = _create_user(db_session, is_active=False).id

    with pytest.raises(RiskDetailBusinessRuleError):
        get_risk_record_detail(
            db_session,
            risk_record_id=risk_record.id,
            requested_by_user_id=user_id,
        )


def test_owner_board_member_and_related_actors_can_read_detail(
    db_session: Session,
) -> None:
    now = datetime.now(timezone.utc)
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    board_member = _create_user(db_session)
    assessment_actor = _create_user(db_session)
    action_owner = _create_user(db_session)
    decision_maker = _create_user(db_session)
    decision_member = _create_user(db_session)
    board = _create_committee(db_session)
    decision_committee = _create_committee(db_session)
    risk_record = _create_risk_record(
        db_session,
        created_by_user_id=creator.id,
        owner_user_id=owner.id,
        board_of_origin_id=board.id,
    )
    _create_committee_membership(
        db_session, committee_id=board.id, user_id=board_member.id
    )
    _create_assessment(
        db_session, risk_record.id, now, assessed_by_user_id=assessment_actor.id
    )
    _create_action(
        db_session, risk_record.id, now, action_owner_user_id=action_owner.id
    )
    _create_decision(
        db_session,
        risk_record.id,
        decision_committee.id,
        now,
        decided_by_user_id=decision_maker.id,
    )
    _create_committee_membership(
        db_session, committee_id=decision_committee.id, user_id=decision_member.id
    )

    for user in (
        creator,
        owner,
        board_member,
        assessment_actor,
        action_owner,
        decision_maker,
        decision_member,
    ):
        assert get_risk_record_detail(
            db_session,
            risk_record_id=risk_record.id,
            requested_by_user_id=user.id,
        ) is not None


@pytest.mark.parametrize("authority_level", [AuthorityLevel.MIDDLE, AuthorityLevel.HIGH])
def test_fixed_governance_members_can_read_detail(
    db_session: Session,
    authority_level: AuthorityLevel,
) -> None:
    reader = _create_user(db_session)
    committee = _create_committee(
        db_session, authority_level=authority_level, is_fixed=True
    )
    _create_committee_membership(db_session, committee_id=committee.id, user_id=reader.id)
    risk_record = _create_risk_record(db_session)

    assert get_risk_record_detail(
        db_session, risk_record_id=risk_record.id, requested_by_user_id=reader.id
    ) is not None


@pytest.mark.parametrize(
    "committee_active,membership_active,authority_level,is_fixed",
    [
        (True, False, AuthorityLevel.LOW, False),
        (False, True, AuthorityLevel.LOW, False),
        (True, True, AuthorityLevel.LOW, False),
    ],
)
def test_unrelated_or_inactive_committee_relationships_do_not_authorize_detail(
    db_session: Session,
    committee_active: bool,
    membership_active: bool,
    authority_level: AuthorityLevel,
    is_fixed: bool,
) -> None:
    reader = _create_user(db_session)
    committee = _create_committee(
        db_session,
        authority_level=authority_level,
        is_fixed=is_fixed,
        is_active=committee_active,
    )
    _create_committee_membership(
        db_session,
        committee_id=committee.id,
        user_id=reader.id,
        is_active=membership_active,
    )
    risk_record = _create_risk_record(db_session)

    with pytest.raises(RiskDetailBusinessRuleError, match="not authorized"):
        get_risk_record_detail(
            db_session,
            risk_record_id=risk_record.id,
            requested_by_user_id=reader.id,
        )


@pytest.mark.parametrize(
    "relationship",
    ["inactive_board_membership", "inactive_decision_membership", "inactive_committee"],
)
def test_inactive_risk_related_committee_relationships_do_not_authorize_detail(
    db_session: Session,
    relationship: str,
) -> None:
    reader = _create_user(db_session)
    committee = _create_committee(
        db_session,
        is_active=relationship != "inactive_committee",
    )
    risk_record = _create_risk_record(
        db_session,
        board_of_origin_id=(
            committee.id if relationship == "inactive_board_membership" else None
        ),
    )
    _create_committee_membership(
        db_session,
        committee_id=committee.id,
        user_id=reader.id,
        is_active=relationship != "inactive_board_membership",
    )
    if relationship != "inactive_board_membership":
        _create_decision(
            db_session,
            risk_record.id,
            committee.id,
            datetime.now(timezone.utc),
        )
        if relationship == "inactive_decision_membership":
            membership = db_session.scalar(
                select(CommitteeMember).where(
                    CommitteeMember.committee_id == committee.id,
                    CommitteeMember.user_id == reader.id,
                )
            )
            assert membership is not None
            membership.is_active = False
            db_session.flush()

    with pytest.raises(RiskDetailBusinessRuleError, match="not authorized"):
        get_risk_record_detail(
            db_session,
            risk_record_id=risk_record.id,
            requested_by_user_id=reader.id,
        )
