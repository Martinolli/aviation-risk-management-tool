import uuid
from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import (
    AuditAction,
    RiskActionStatus,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskRecord
from app.schemas.risk_action import RiskActionCreate, RiskActionUpdate
from app.services.risk_action_service import (
    RiskActionBusinessRuleError,
    complete_risk_action,
    create_risk_action,
    get_risk_action,
    list_risk_actions,
    update_risk_action,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("risk action service must not commit transactions")


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
    workflow_status: RiskWorkflowStatus = RiskWorkflowStatus.DRAFT,
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


def _action_data(
    risk_record_id: uuid.UUID,
    *,
    title: str = "Inspect flight test instrumentation",
) -> RiskActionCreate:
    return RiskActionCreate(
        risk_record_id=risk_record_id,
        title=title,
        description="Mitigation action",
        due_date=date(2026, 6, 30),
    )


def test_create_action_succeeds(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)

    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    assert action.id is not None
    assert action.title == "Inspect flight test instrumentation"


def test_created_action_status_is_open(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)

    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    assert action.status == RiskActionStatus.OPEN
    assert action.completed_at is None


def test_create_action_for_unknown_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    with pytest.raises(RiskActionBusinessRuleError):
        create_risk_action(db_session, data=_action_data(uuid.uuid4()))


def test_create_action_for_inactive_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session, is_active=False)

    with pytest.raises(RiskActionBusinessRuleError):
        create_risk_action(db_session, data=_action_data(risk_record.id))


def test_create_action_for_closed_risk_record_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(
        db_session,
        workflow_status=RiskWorkflowStatus.CLOSED,
    )

    with pytest.raises(RiskActionBusinessRuleError):
        create_risk_action(db_session, data=_action_data(risk_record.id))


def test_create_action_with_empty_title_fails() -> None:
    with pytest.raises(ValidationError):
        RiskActionCreate(risk_record_id=uuid.uuid4(), title="")


def test_create_action_with_blank_title_fails_at_service_level(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)

    with pytest.raises(RiskActionBusinessRuleError):
        create_risk_action(db_session, data=_action_data(risk_record.id, title="   "))


def test_create_action_writes_create_audit_log(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)

    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == action.id,
            AuditLog.entity_type == "RiskAction",
            AuditLog.action == AuditAction.CREATE,
        )
    )

    assert audit_log is not None


def test_update_action_title_succeeds_and_writes_update_audit_log(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    updated_action = update_risk_action(
        db_session,
        risk_action_id=action.id,
        data=RiskActionUpdate(title="Revise inspection plan"),
        reason="Clarify mitigation",
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == action.id,
            AuditLog.entity_type == "RiskAction",
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "title",
        )
    )

    assert updated_action.title == "Revise inspection plan"
    assert audit_log is not None
    assert audit_log.old_value == "Inspect flight test instrumentation"
    assert audit_log.new_value == "Revise inspection plan"


def test_update_action_with_empty_title_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    with pytest.raises(RiskActionBusinessRuleError):
        update_risk_action(
            db_session,
            risk_action_id=action.id,
            data=RiskActionUpdate(title="   "),
        )


def test_update_action_to_completed_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    with pytest.raises(RiskActionBusinessRuleError):
        update_risk_action(
            db_session,
            risk_action_id=action.id,
            data=RiskActionUpdate(status=RiskActionStatus.COMPLETED),
        )


def test_complete_action_succeeds(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    completed_action = complete_risk_action(
        db_session,
        risk_action_id=action.id,
        completion_notes="Inspection completed",
    )

    assert completed_action.status == RiskActionStatus.COMPLETED
    assert completed_action.completion_notes == "Inspection completed"

    audit_fields = set(
        db_session.scalars(
            select(AuditLog.field_name).where(
                AuditLog.entity_id == action.id,
                AuditLog.entity_type == "RiskAction",
                AuditLog.action == AuditAction.UPDATE,
            )
        )
    )

    assert {"status", "completed_at", "completion_notes"}.issubset(audit_fields)


def test_completed_action_has_completed_at_set(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    action = create_risk_action(db_session, data=_action_data(risk_record.id))

    completed_action = complete_risk_action(db_session, risk_action_id=action.id)

    assert completed_action.completed_at is not None
    assert completed_action.completed_at.tzinfo is not None


def test_completing_already_completed_action_raises_business_rule_error(
    db_session: Session,
) -> None:
    risk_record = _create_risk_record(db_session)
    action = create_risk_action(db_session, data=_action_data(risk_record.id))
    complete_risk_action(db_session, risk_action_id=action.id)

    with pytest.raises(RiskActionBusinessRuleError):
        complete_risk_action(db_session, risk_action_id=action.id)


def test_completed_action_cannot_be_updated(db_session: Session) -> None:
    risk_record = _create_risk_record(db_session)
    action = create_risk_action(db_session, data=_action_data(risk_record.id))
    complete_risk_action(db_session, risk_action_id=action.id)

    with pytest.raises(RiskActionBusinessRuleError):
        update_risk_action(
            db_session,
            risk_action_id=action.id,
            data=RiskActionUpdate(title="Reopened title"),
        )


def test_list_risk_actions_filtered_by_risk_record_id(db_session: Session) -> None:
    first_risk = _create_risk_record(db_session)
    second_risk = _create_risk_record(db_session)
    first_action = create_risk_action(db_session, data=_action_data(first_risk.id))
    second_action = create_risk_action(db_session, data=_action_data(second_risk.id))

    actions = list_risk_actions(db_session, risk_record_id=first_risk.id)

    assert first_action in actions
    assert second_action not in actions


def test_get_unknown_action_returns_none(db_session: Session) -> None:
    assert get_risk_action(db_session, risk_action_id=uuid.uuid4()) is None
