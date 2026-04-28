import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import AuditAction, RiskWorkflowStatus
from app.services.audit_service import (
    log_archive_action,
    log_change,
    log_entity_created,
    log_llm_analysis,
    log_report_generated,
    log_workflow_action,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("audit service must not commit transactions")


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


def test_log_entity_created_creates_create_action(db_session: Session) -> None:
    entity_id = uuid.uuid4()

    audit_log = log_entity_created(
        db_session,
        entity_type="RiskRecord",
        entity_id=entity_id,
        new_value={"risk_id": "RISK-001"},
        reason="Initial creation",
    )

    assert audit_log.id is not None
    assert audit_log.action == AuditAction.CREATE
    assert audit_log.entity_id == entity_id
    assert audit_log.field_name is None
    assert audit_log.new_value == {"risk_id": "RISK-001"}
    assert audit_log.changed_at.tzinfo is not None


def test_log_change_creates_update_and_stores_old_new_values(
    db_session: Session,
) -> None:
    audit_log = log_change(
        db_session,
        entity_type="RiskRecord",
        entity_id=uuid.uuid4(),
        field_name="workflow_status",
        old_value=RiskWorkflowStatus.DRAFT,
        new_value=RiskWorkflowStatus.SUBMITTED_TO_OPERATIONAL_BOARD,
        reason="Submitted for board review",
    )

    assert audit_log.action == AuditAction.UPDATE
    assert audit_log.field_name == "workflow_status"
    assert audit_log.old_value == "DRAFT"
    assert audit_log.new_value == "SUBMITTED_TO_OPERATIONAL_BOARD"


def test_log_workflow_action_accepts_submit(db_session: Session) -> None:
    audit_log = log_workflow_action(
        db_session,
        entity_type="RiskRecord",
        entity_id=uuid.uuid4(),
        action=AuditAction.SUBMIT,
        new_value={"workflow_status": "SUBMITTED_TO_OPERATIONAL_BOARD"},
    )

    assert audit_log.action == AuditAction.SUBMIT


def test_log_workflow_action_rejects_non_workflow_action(db_session: Session) -> None:
    with pytest.raises(ValueError):
        log_workflow_action(
            db_session,
            entity_type="RiskRecord",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
        )


def test_log_archive_action_creates_archive_action(db_session: Session) -> None:
    audit_log = log_archive_action(
        db_session,
        entity_type="Committee",
        entity_id=uuid.uuid4(),
        reason="Board deactivated",
    )

    assert audit_log.action == AuditAction.ARCHIVE
    assert audit_log.reason == "Board deactivated"


def test_log_report_generated_creates_generate_report_action(
    db_session: Session,
) -> None:
    audit_log = log_report_generated(
        db_session,
        entity_type="GeneratedReport",
        entity_id=uuid.uuid4(),
        report_metadata={"template_version": "1.0", "file_hash": "abc123"},
    )

    assert audit_log.action == AuditAction.GENERATE_REPORT
    assert audit_log.new_value == {"template_version": "1.0", "file_hash": "abc123"}


def test_log_llm_analysis_creates_llm_analysis_action(db_session: Session) -> None:
    audit_log = log_llm_analysis(
        db_session,
        entity_type="LLMAnalysis",
        entity_id=uuid.uuid4(),
        llm_metadata={"model_name": "example-model", "is_accepted": False},
    )

    assert audit_log.action == AuditAction.LLM_ANALYSIS
    assert audit_log.new_value == {"model_name": "example-model", "is_accepted": False}


def test_uuid_and_datetime_values_are_json_compatible_strings(
    db_session: Session,
) -> None:
    value_id = uuid.uuid4()
    timestamp = datetime(2026, 4, 28, 10, 30, tzinfo=timezone.utc)

    audit_log = log_change(
        db_session,
        entity_type="RiskRecord",
        entity_id=uuid.uuid4(),
        field_name="metadata",
        old_value={"id": value_id, "changed_at": timestamp},
        new_value={"items": [value_id, timestamp]},
    )

    assert audit_log.old_value == {
        "id": str(value_id),
        "changed_at": timestamp.isoformat(),
    }
    assert audit_log.new_value == {
        "items": [str(value_id), timestamp.isoformat()],
    }


def test_audit_service_adds_and_flushes_without_commit(db_session: Session) -> None:
    audit_log = log_entity_created(
        db_session,
        entity_type="RiskRecord",
        entity_id=uuid.uuid4(),
    )

    saved_log = db_session.scalar(select(AuditLog).where(AuditLog.id == audit_log.id))

    assert saved_log is audit_log
