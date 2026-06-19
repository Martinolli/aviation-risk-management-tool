import uuid
from datetime import datetime, timezone

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
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.schemas.risk import RiskRecordCreate, RiskRecordUpdate
from app.services.risk_service import (
    RiskRecordBusinessRuleError,
    create_risk_record,
    list_risk_records,
    submit_risk_record,
    update_risk_record,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("risk service must not commit transactions")


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


def _risk_data(**overrides: object) -> RiskRecordCreate:
    data = {
        "problem_description": "Unexpected vibration observed during taxi test.",
        "domain": RiskDomain.FLIGHT_TEST,
    }
    data.update(overrides)
    return RiskRecordCreate(**data)


def _create_board(
    db_session: Session,
    *,
    is_active: bool = True,
) -> Committee:
    committee = Committee(
        name=f"Operational Board-{uuid.uuid4()}",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=False,
        is_active=is_active,
    )
    db_session.add(committee)
    db_session.flush()
    return committee


def test_create_risk_with_required_problem_description_succeeds(
    db_session: Session,
) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())

    assert risk_record.id is not None
    assert risk_record.problem_description == (
        "Unexpected vibration observed during taxi test."
    )


def test_create_risk_with_empty_problem_description_fails() -> None:
    with pytest.raises(ValidationError):
        RiskRecordCreate(problem_description="")


def test_create_risk_with_blank_problem_description_fails_at_service_level(
    db_session: Session,
) -> None:
    with pytest.raises(RiskRecordBusinessRuleError):
        create_risk_record(
            db_session,
            data=RiskRecordCreate(problem_description="   "),
        )


def test_created_risk_has_initial_statuses_and_is_active(db_session: Session) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())

    assert risk_record.workflow_status == RiskWorkflowStatus.DRAFT
    assert risk_record.lifecycle_status == RiskLifecycleStatus.OPEN
    assert risk_record.is_active is True


def test_create_risk_record_assigns_risk_id_automatically(
    db_session: Session,
) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())

    assert risk_record.risk_id is not None
    assert risk_record.risk_id.startswith("RISK-")


def test_creating_two_risks_assigns_sequential_risk_ids(db_session: Session) -> None:
    first_risk = create_risk_record(db_session, data=_risk_data())
    second_risk = create_risk_record(
        db_session,
        data=_risk_data(problem_description="Second risk."),
    )

    assert first_risk.risk_id is not None
    assert second_risk.risk_id is not None
    assert int(second_risk.risk_id[-4:]) == int(first_risk.risk_id[-4:]) + 1


def test_create_risk_with_active_board_of_origin_succeeds(
    db_session: Session,
) -> None:
    board = _create_board(db_session)

    risk_record = create_risk_record(
        db_session,
        data=_risk_data(board_of_origin_id=board.id),
    )

    assert risk_record.board_of_origin_id == board.id


def test_create_risk_with_unknown_board_of_origin_raises_business_rule_error(
    db_session: Session,
) -> None:
    with pytest.raises(RiskRecordBusinessRuleError):
        create_risk_record(
            db_session,
            data=_risk_data(board_of_origin_id=uuid.uuid4()),
        )


def test_create_risk_with_inactive_board_of_origin_raises_business_rule_error(
    db_session: Session,
) -> None:
    board = _create_board(db_session, is_active=False)

    with pytest.raises(RiskRecordBusinessRuleError):
        create_risk_record(
            db_session,
            data=_risk_data(board_of_origin_id=board.id),
        )


def test_create_risk_writes_create_audit_log(db_session: Session) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.entity_type == "RiskRecord",
            AuditLog.action == AuditAction.CREATE,
        )
    )

    assert audit_log is not None


def test_create_risk_audit_snapshot_includes_generated_risk_id(
    db_session: Session,
) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.entity_type == "RiskRecord",
            AuditLog.action == AuditAction.CREATE,
        )
    )

    assert audit_log is not None
    assert audit_log.new_value["risk_id"] == risk_record.risk_id


def test_update_risk_field_succeeds_and_writes_update_audit_log(
    db_session: Session,
) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())

    updated_risk = update_risk_record(
        db_session,
        risk_record_id=risk_record.id,
        data=RiskRecordUpdate(source_trigger="Pilot report"),
        reason="Clarify trigger",
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.entity_type == "RiskRecord",
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "source_trigger",
        )
    )

    assert updated_risk.source_trigger == "Pilot report"
    assert audit_log is not None
    assert audit_log.old_value is None
    assert audit_log.new_value == "Pilot report"
    assert audit_log.reason == "Clarify trigger"


def test_update_does_not_allow_changing_problem_description() -> None:
    with pytest.raises(ValidationError):
        RiskRecordUpdate(problem_description="Changed problem description")


def test_update_archived_inactive_risk_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())
    risk_record.is_active = False
    risk_record.archived_at = datetime.now(timezone.utc)
    db_session.flush()

    with pytest.raises(RiskRecordBusinessRuleError):
        update_risk_record(
            db_session,
            risk_record_id=risk_record.id,
            data=RiskRecordUpdate(source_trigger="New trigger"),
        )


def test_submit_draft_risk_succeeds_and_writes_submit_audit_log(
    db_session: Session,
) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())

    submitted_risk = submit_risk_record(
        db_session,
        risk_record_id=risk_record.id,
        reason="Ready for board review",
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.entity_type == "RiskRecord",
            AuditLog.action == AuditAction.SUBMIT,
        )
    )

    assert (
        submitted_risk.workflow_status
        == RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD
    )
    assert audit_log is not None
    assert audit_log.reason == "Ready for board review"


def test_submit_non_draft_risk_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = create_risk_record(db_session, data=_risk_data())
    submit_risk_record(db_session, risk_record_id=risk_record.id)

    with pytest.raises(RiskRecordBusinessRuleError):
        submit_risk_record(db_session, risk_record_id=risk_record.id)


def test_list_risk_records_excludes_archived_by_default(
    db_session: Session,
) -> None:
    active_risk = create_risk_record(db_session, data=_risk_data())
    archived_risk = create_risk_record(
        db_session,
        data=_risk_data(problem_description="Archived risk."),
    )
    archived_risk.is_active = False
    archived_risk.archived_at = datetime.now(timezone.utc)
    db_session.flush()

    risk_records = list_risk_records(db_session)

    assert active_risk in risk_records
    assert archived_risk not in risk_records


def test_list_risk_records_includes_archived_when_requested(
    db_session: Session,
) -> None:
    active_risk = create_risk_record(db_session, data=_risk_data())
    archived_risk = create_risk_record(
        db_session,
        data=_risk_data(problem_description="Archived risk."),
    )
    archived_risk.is_active = False
    archived_risk.archived_at = datetime.now(timezone.utc)
    db_session.flush()

    risk_records = list_risk_records(db_session, include_archived=True)

    assert active_risk in risk_records
    assert archived_risk in risk_records
