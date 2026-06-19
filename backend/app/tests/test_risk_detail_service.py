import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
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
    RiskActionStatus,
    RiskAssessmentType,
    RiskDecisionType,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskAction, RiskAssessment, RiskDecision, RiskRecord
from app.services.risk_detail_service import (
    RiskDetailNotFoundError,
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


def _create_risk_record(db_session: Session, *, is_active: bool = True) -> RiskRecord:
    risk_record = RiskRecord(
        risk_id=f"RISK-2026-{uuid.uuid4().int % 9999:04d}",
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=is_active,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


def _create_committee(db_session: Session) -> Committee:
    committee = Committee(
        name=f"Committee {uuid.uuid4()}",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=False,
        is_active=True,
    )
    db_session.add(committee)
    db_session.flush()
    return committee


def _set_created_at(db_session: Session, model, created_at: datetime) -> None:
    model.created_at = created_at
    model.updated_at = created_at
    db_session.flush()


def _create_assessment(
    db_session: Session,
    risk_record_id: uuid.UUID,
    created_at: datetime,
    assessment_type: RiskAssessmentType = RiskAssessmentType.INITIAL,
) -> RiskAssessment:
    assessment = RiskAssessment(
        risk_record_id=risk_record_id,
        assessment_type=assessment_type,
        severity="Major",
        likelihood="Remote",
        risk_level="Medium",
        assessed_at=created_at,
    )
    db_session.add(assessment)
    db_session.flush()
    _set_created_at(db_session, assessment, created_at)
    return assessment


def _create_action(
    db_session: Session,
    risk_record_id: uuid.UUID,
    created_at: datetime,
) -> RiskAction:
    action = RiskAction(
        risk_record_id=risk_record_id,
        title=f"Action {uuid.uuid4()}",
        status=RiskActionStatus.OPEN,
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
) -> RiskDecision:
    decision = RiskDecision(
        risk_record_id=risk_record_id,
        committee_id=committee_id,
        decision_type=RiskDecisionType.APPROVE,
        decision_text="Approved.",
        decided_at=decided_at,
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

    detail = get_risk_record_detail(db_session, risk_record_id=risk_record.id)

    assert detail["risk_record"] is risk_record


def test_detail_includes_related_resources_for_the_risk(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    risk_record = _create_risk_record(db_session)
    committee = _create_committee(db_session)
    assessment = _create_assessment(db_session, risk_record.id, now)
    action = _create_action(db_session, risk_record.id, now)
    decision = _create_decision(db_session, risk_record.id, committee.id, now)

    detail = get_risk_record_detail(db_session, risk_record_id=risk_record.id)

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

    detail = get_risk_record_detail(db_session, risk_record_id=target_risk.id)

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

    detail = get_risk_record_detail(db_session, risk_record_id=risk_record.id)

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

    detail = get_risk_record_detail(db_session, risk_record_id=risk_record.id)
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

    detail = get_risk_record_detail(db_session, risk_record_id=risk_record.id)

    assert detail["risk_record"] is risk_record


def test_unknown_risk_raises_not_found(db_session: Session) -> None:
    with pytest.raises(RiskDetailNotFoundError):
        get_risk_record_detail(db_session, risk_record_id=uuid.uuid4())
