import uuid

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee
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
) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=workflow_status,
        lifecycle_status=RiskLifecycleStatus.OPEN,
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
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session, authority_level=authority_level)
    decision = create_risk_decision(
        db_session,
        data=_decision_data(
            risk_record.id,
            committee.id,
            decision_type=decision_type,
        ),
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

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(
                risk_record.id,
                committee.id,
                decision_type=RiskDecisionType.ESCALATE,
            ),
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

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(
                risk_record.id,
                committee.id,
                decision_type=RiskDecisionType.ACCEPT_RESIDUAL_RISK,
            ),
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

    with pytest.raises(RiskDecisionBusinessRuleError):
        create_risk_decision(
            db_session,
            data=_decision_data(
                risk_record.id,
                committee.id,
                decision_type=RiskDecisionType.CLOSE,
            ),
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
    first_risk = _create_risk_record(db_session)
    second_risk = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    first_decision = create_risk_decision(
        db_session,
        data=_decision_data(first_risk.id, committee.id),
    )
    second_decision = create_risk_decision(
        db_session,
        data=_decision_data(second_risk.id, committee.id),
    )

    decisions = list_risk_decisions(db_session, risk_record_id=first_risk.id)

    assert first_decision in decisions
    assert second_decision not in decisions


def test_list_risk_decisions_filtered_by_committee_id(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    first_committee = _create_committee(db_session)
    second_committee = _create_committee(db_session)
    first_decision = create_risk_decision(
        db_session,
        data=_decision_data(risk_record.id, first_committee.id),
    )
    second_decision = create_risk_decision(
        db_session,
        data=_decision_data(risk_record.id, second_committee.id),
    )

    decisions = list_risk_decisions(db_session, committee_id=first_committee.id)

    assert first_decision in decisions
    assert second_decision not in decisions


def test_get_unknown_decision_returns_none(db_session: Session) -> None:
    assert get_risk_decision(db_session, risk_decision_id=uuid.uuid4()) is None
