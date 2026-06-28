import uuid

import pytest
from pydantic import ValidationError
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
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskRecord
from app.models.user import User
from app.schemas.risk_decision import RiskDecisionCreate
from app.services.risk_decision_service import (
    RiskDecisionBusinessRuleError,
    create_risk_decision,
    get_risk_decision,
    list_risk_decisions,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("risk decision service must not commit transactions")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, class_=NoCommitSession)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


def _create_risk_record(
    db_session: Session,
    *,
    is_active: bool = True,
    workflow_status: RiskWorkflowStatus = (
        RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD
    ),
    board_of_origin_id: uuid.UUID | None = None,
) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=workflow_status,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        board_of_origin_id=board_of_origin_id,
        is_active=is_active,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


def _committee_type(authority_level: AuthorityLevel) -> CommitteeType:
    if authority_level == AuthorityLevel.LOW:
        return CommitteeType.OPERATIONAL_BOARD
    if authority_level == AuthorityLevel.MIDDLE:
        return CommitteeType.RISK_MANAGEMENT_COMMITTEE
    return CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE


def _create_committee(
    db_session: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_active: bool = True,
) -> Committee:
    committee = Committee(
        name=f"{authority_level.value} Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=_committee_type(authority_level),
        is_fixed=authority_level != AuthorityLevel.LOW,
        is_active=is_active,
    )
    db_session.add(committee)
    db_session.flush()
    return committee


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Decision User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_membership(
    db_session: Session,
    *,
    committee: Committee,
    user: User,
    is_active: bool = True,
) -> CommitteeMember:
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        is_active=is_active,
    )
    db_session.add(membership)
    db_session.flush()
    return membership


def _create_decision_user(db_session: Session, committee: Committee) -> User:
    user = _create_user(db_session)
    _create_membership(db_session, committee=committee, user=user)
    return user


def _decision_data(
    risk_record_id: uuid.UUID,
    committee_id: uuid.UUID,
    *,
    decision_type: RiskDecisionType = RiskDecisionType.APPROVE,
    decision_text: str = "Committee decision recorded.",
) -> RiskDecisionCreate:
    return RiskDecisionCreate(
        risk_record_id=risk_record_id,
        committee_id=committee_id,
        decision_type=decision_type,
        decision_text=decision_text,
    )


def _create_decision_for_authority(
    db_session: Session,
    authority_level: AuthorityLevel,
    decision_type: RiskDecisionType,
):
    committee = _create_committee(db_session, authority_level=authority_level)
    workflow_status = {
        AuthorityLevel.LOW: RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        AuthorityLevel.MIDDLE: (
            RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE
        ),
        AuthorityLevel.HIGH: RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE,
    }[authority_level]
    risk_record = _create_risk_record(
        db_session,
        workflow_status=workflow_status,
        board_of_origin_id=(
            committee.id if authority_level == AuthorityLevel.LOW else None
        ),
    )
    user = _create_decision_user(db_session, committee)
    decision = create_risk_decision(
        db_session,
        data=_decision_data(
            risk_record.id,
            committee.id,
            decision_type=decision_type,
        ),
        decided_by_user_id=user.id,
    )
    return risk_record, committee, decision


def test_create_approve_decision_by_low_committee_succeeds(
    db_session: Session,
) -> None:
    _risk_record, _committee, decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.LOW,
        RiskDecisionType.APPROVE,
    )

    assert decision.id is not None
    assert decision.decision_type == RiskDecisionType.APPROVE
    assert decision.decided_at.tzinfo is not None


def test_low_approve_changes_workflow_status(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.LOW,
        RiskDecisionType.APPROVE,
    )

    assert (
        risk_record.workflow_status
        == RiskWorkflowStatus.APPROVED_AT_OPERATIONAL_BOARD
    )


def test_middle_approve_changes_workflow_status(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.MIDDLE,
        RiskDecisionType.APPROVE,
    )

    assert (
        risk_record.workflow_status
        == RiskWorkflowStatus.APPROVED_AT_RISK_MANAGEMENT_COMMITTEE
    )


def test_high_approve_changes_workflow_status_to_accepted(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.HIGH,
        RiskDecisionType.APPROVE,
    )

    assert risk_record.workflow_status == RiskWorkflowStatus.ACCEPTED


def test_reject_decision_changes_workflow_status(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.LOW,
        RiskDecisionType.REJECT,
    )

    assert risk_record.workflow_status == RiskWorkflowStatus.REJECTED


def test_low_escalate_changes_workflow_status(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.LOW,
        RiskDecisionType.ESCALATE,
    )

    assert (
        risk_record.workflow_status
        == RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE
    )


def test_middle_escalate_changes_workflow_status(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.MIDDLE,
        RiskDecisionType.ESCALATE,
    )

    assert (
        risk_record.workflow_status
        == RiskWorkflowStatus.ESCALATED_TO_EXECUTIVE_COMMITTEE
    )


def test_high_escalate_raises_business_rule_error(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session, authority_level=AuthorityLevel.HIGH)
    user = _create_decision_user(db_session, committee)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(
                risk_record.id,
                committee.id,
                decision_type=RiskDecisionType.ESCALATE,
            ),
            decided_by_user_id=user.id,
        )


def test_return_for_revision_changes_workflow_status(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.LOW,
        RiskDecisionType.RETURN_FOR_REVISION,
    )

    assert risk_record.workflow_status == RiskWorkflowStatus.RETURNED_FOR_REVISION


def test_accept_residual_risk_by_middle_succeeds(db_session: Session) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.MIDDLE,
        RiskDecisionType.ACCEPT_RESIDUAL_RISK,
    )

    assert risk_record.workflow_status == RiskWorkflowStatus.ACCEPTED


def test_accept_residual_risk_by_low_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session, authority_level=AuthorityLevel.LOW)
    user = _create_decision_user(db_session, committee)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(
                risk_record.id,
                committee.id,
                decision_type=RiskDecisionType.ACCEPT_RESIDUAL_RISK,
            ),
            decided_by_user_id=user.id,
        )


@pytest.mark.parametrize("authority_level", [AuthorityLevel.MIDDLE, AuthorityLevel.HIGH])
def test_close_by_middle_or_high_changes_workflow_and_lifecycle_status(
    db_session: Session,
    authority_level: AuthorityLevel,
) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        authority_level,
        RiskDecisionType.CLOSE,
    )

    assert risk_record.workflow_status == RiskWorkflowStatus.CLOSED
    assert risk_record.lifecycle_status == RiskLifecycleStatus.CLOSED


def test_close_by_low_raises_business_rule_error(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session, authority_level=AuthorityLevel.LOW)
    user = _create_decision_user(db_session, committee)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(
                risk_record.id,
                committee.id,
                decision_type=RiskDecisionType.CLOSE,
            ),
            decided_by_user_id=user.id,
        )


def test_create_decision_for_unknown_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    committee = _create_committee(db_session)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(uuid.uuid4(), committee.id),
        )


def test_create_decision_for_inactive_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session, is_active=False)
    committee = _create_committee(db_session)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, committee.id),
        )


def test_create_decision_for_closed_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(
        db_session,
        workflow_status=RiskWorkflowStatus.CLOSED,
    )
    committee = _create_committee(db_session)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, committee.id),
        )


def test_create_decision_for_unknown_committee_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, uuid.uuid4()),
        )


def test_create_decision_for_inactive_committee_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session, is_active=False)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, committee.id),
        )


def test_empty_decision_text_fails_schema_validation() -> None:
    with pytest.raises(ValidationError):
        RiskDecisionCreate(
            risk_record_id=uuid.uuid4(),
            committee_id=uuid.uuid4(),
            decision_type=RiskDecisionType.APPROVE,
            decision_text="",
        )


def test_blank_decision_text_raises_business_rule_error(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, committee.id, decision_text="   "),
        )


def test_decision_requires_an_active_authenticated_member(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)

    with pytest.raises(
        RiskDecisionBusinessRuleError,
        match="authenticated active user",
    ):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, committee.id),
        )


def test_decision_rejects_unknown_or_inactive_user(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    inactive_user = _create_user(db_session, is_active=False)

    with pytest.raises(RiskDecisionBusinessRuleError, match="user does not exist"):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, committee.id),
            decided_by_user_id=uuid.uuid4(),
        )
    with pytest.raises(RiskDecisionBusinessRuleError, match="user is inactive"):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, committee.id),
            decided_by_user_id=inactive_user.id,
        )


def test_decision_rejects_inactive_committee_or_invalid_membership(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    user = _create_user(db_session)
    inactive_committee = _create_committee(db_session, is_active=False)
    active_committee = _create_committee(db_session)

    with pytest.raises(RiskDecisionBusinessRuleError, match="committee is inactive"):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, inactive_committee.id),
            decided_by_user_id=user.id,
        )
    with pytest.raises(RiskDecisionBusinessRuleError, match="not an active member"):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, active_committee.id),
            decided_by_user_id=user.id,
        )

    _create_membership(
        db_session,
        committee=active_committee,
        user=user,
        is_active=False,
    )
    with pytest.raises(RiskDecisionBusinessRuleError, match="not an active member"):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, active_committee.id),
            decided_by_user_id=user.id,
        )

    other_committee = _create_committee(db_session)
    _create_membership(db_session, committee=other_committee, user=user)
    with pytest.raises(RiskDecisionBusinessRuleError, match="not an active member"):
        create_risk_decision(
            db_session,
            data=_decision_data(risk_record.id, active_committee.id),
            decided_by_user_id=user.id,
        )


def test_authorized_decision_stores_and_audits_decider(db_session: Session) -> None:
    committee = _create_committee(db_session)
    risk_record = _create_risk_record(db_session, board_of_origin_id=committee.id)
    user = _create_decision_user(db_session, committee)

    decision = create_risk_decision(
        db_session,
        data=_decision_data(risk_record.id, committee.id),
        decided_by_user_id=user.id,
    )
    workflow_audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.action == AuditAction.APPROVE,
        )
    )

    assert decision.decided_by_user_id == user.id
    assert workflow_audit_log is not None
    assert workflow_audit_log.changed_by_user_id == user.id


def test_create_decision_writes_create_audit_log(db_session: Session) -> None:
    risk_record, _committee, decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.LOW,
        RiskDecisionType.APPROVE,
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == decision.id,
            AuditLog.entity_type == "RiskDecision",
            AuditLog.action == AuditAction.CREATE,
        )
    )

    assert risk_record.id is not None
    assert audit_log is not None


def test_workflow_changing_decision_writes_workflow_audit_log(
    db_session: Session,
) -> None:
    risk_record, _committee, _decision = _create_decision_for_authority(
        db_session,
        AuthorityLevel.LOW,
        RiskDecisionType.ESCALATE,
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.entity_type == "RiskRecord",
            AuditLog.action == AuditAction.ESCALATE,
        )
    )

    assert audit_log is not None


def test_list_risk_decisions_filtered_by_risk_record_id(
    db_session: Session,
) -> None:
    committee = _create_committee(db_session)
    first_risk = _create_risk_record(db_session, board_of_origin_id=committee.id)
    second_risk = _create_risk_record(db_session, board_of_origin_id=committee.id)
    user = _create_decision_user(db_session, committee)
    first_decision = create_risk_decision(
        db_session,
        data=_decision_data(first_risk.id, committee.id),
        decided_by_user_id=user.id,
    )
    second_decision = create_risk_decision(
        db_session,
        data=_decision_data(second_risk.id, committee.id),
        decided_by_user_id=user.id,
    )

    decisions = list_risk_decisions(db_session, risk_record_id=first_risk.id)

    assert first_decision in decisions
    assert second_decision not in decisions


def test_list_risk_decisions_filtered_by_committee_id(db_session: Session) -> None:
    first_committee = _create_committee(db_session)
    second_committee = _create_committee(db_session)
    first_risk = _create_risk_record(
        db_session, board_of_origin_id=first_committee.id
    )
    second_risk = _create_risk_record(
        db_session, board_of_origin_id=second_committee.id
    )
    first_user = _create_decision_user(db_session, first_committee)
    second_user = _create_decision_user(db_session, second_committee)
    first_decision = create_risk_decision(
        db_session,
        data=_decision_data(first_risk.id, first_committee.id),
        decided_by_user_id=first_user.id,
    )
    second_decision = create_risk_decision(
        db_session,
        data=_decision_data(second_risk.id, second_committee.id),
        decided_by_user_id=second_user.id,
    )

    decisions = list_risk_decisions(db_session, committee_id=first_committee.id)

    assert first_decision in decisions
    assert second_decision not in decisions


def test_get_unknown_decision_returns_none(db_session: Session) -> None:
    assert get_risk_decision(db_session, risk_decision_id=uuid.uuid4()) is None


def test_low_member_from_other_committee_cannot_decide_risk(
    db_session: Session,
) -> None:
    board_of_origin = _create_committee(db_session)
    other_board = _create_committee(db_session)
    other_member = _create_decision_user(db_session, other_board)
    risk = _create_risk_record(
        db_session, board_of_origin_id=board_of_origin.id
    )

    with pytest.raises(RiskDecisionBusinessRuleError, match="Board of Origin"):
        create_risk_decision(
            db_session,
            data=_decision_data(risk.id, other_board.id),
            decided_by_user_id=other_member.id,
        )


def test_middle_committee_can_decide_only_risks_escalated_to_rmc(
    db_session: Session,
) -> None:
    rmc = _create_committee(db_session, authority_level=AuthorityLevel.MIDDLE)
    member = _create_decision_user(db_session, rmc)
    escalated = _create_risk_record(
        db_session,
        workflow_status=RiskWorkflowStatus.ESCALATED_TO_RISK_MANAGEMENT_COMMITTEE,
    )
    not_escalated = _create_risk_record(db_session)

    assert create_risk_decision(
        db_session,
        data=_decision_data(escalated.id, rmc.id),
        decided_by_user_id=member.id,
    ).id is not None
    with pytest.raises(RiskDecisionBusinessRuleError, match="cannot decide"):
        create_risk_decision(
            db_session,
            data=_decision_data(not_escalated.id, rmc.id),
            decided_by_user_id=member.id,
        )
