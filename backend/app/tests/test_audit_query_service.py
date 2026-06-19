import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import AuditAction
from app.services.audit_query_service import (
    AuditQueryBusinessRuleError,
    get_audit_log,
    list_audit_logs,
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


def _create_audit_log(
    db_session: Session,
    *,
    entity_type: str = "RiskRecord",
    entity_id: uuid.UUID | None = None,
    action: AuditAction = AuditAction.CREATE,
    changed_by_user_id: uuid.UUID | None = None,
    changed_at: datetime | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id or uuid.uuid4(),
        action=action,
        field_name=None,
        old_value=None,
        new_value={"created": True},
        changed_by_user_id=changed_by_user_id,
        changed_at=changed_at or datetime.now(timezone.utc),
        reason=None,
    )
    db_session.add(audit_log)
    db_session.flush()
    return audit_log


def _seed_logs(db_session: Session) -> list[AuditLog]:
    now = datetime.now(timezone.utc)
    older = _create_audit_log(
        db_session,
        entity_type="Committee",
        action=AuditAction.UPDATE,
        changed_at=now - timedelta(minutes=2),
    )
    middle = _create_audit_log(
        db_session,
        entity_type="RiskRecord",
        action=AuditAction.CREATE,
        changed_at=now - timedelta(minutes=1),
    )
    newest = _create_audit_log(
        db_session,
        entity_type="RiskAction",
        action=AuditAction.ARCHIVE,
        changed_at=now,
    )
    return [older, middle, newest]


def test_get_audit_log_returns_existing_audit_log(db_session: Session) -> None:
    audit_log = _create_audit_log(db_session)

    assert get_audit_log(db_session, audit_log_id=audit_log.id) is audit_log


def test_get_audit_log_returns_none_for_unknown_audit_log(
    db_session: Session,
) -> None:
    assert get_audit_log(db_session, audit_log_id=uuid.uuid4()) is None


def test_list_audit_logs_returns_logs_ordered_by_changed_at_descending(
    db_session: Session,
) -> None:
    older, middle, newest = _seed_logs(db_session)

    logs = list_audit_logs(db_session)

    assert logs == [newest, middle, older]


def test_list_audit_logs_filters_by_entity_type(db_session: Session) -> None:
    _seed_logs(db_session)

    logs = list_audit_logs(db_session, entity_type="RiskRecord")

    assert len(logs) == 1
    assert logs[0].entity_type == "RiskRecord"


def test_list_audit_logs_filters_by_entity_id(db_session: Session) -> None:
    target_entity_id = uuid.uuid4()
    target = _create_audit_log(db_session, entity_id=target_entity_id)
    _create_audit_log(db_session)

    logs = list_audit_logs(db_session, entity_id=target_entity_id)

    assert logs == [target]


def test_list_audit_logs_filters_by_action(db_session: Session) -> None:
    _seed_logs(db_session)

    logs = list_audit_logs(db_session, action=AuditAction.UPDATE)

    assert len(logs) == 1
    assert logs[0].action == AuditAction.UPDATE


def test_list_audit_logs_filters_by_changed_by_user_id(db_session: Session) -> None:
    user_id = uuid.uuid4()
    target = _create_audit_log(db_session, changed_by_user_id=user_id)
    _create_audit_log(db_session, changed_by_user_id=uuid.uuid4())

    logs = list_audit_logs(db_session, changed_by_user_id=user_id)

    assert logs == [target]


def test_list_audit_logs_applies_limit(db_session: Session) -> None:
    _seed_logs(db_session)

    logs = list_audit_logs(db_session, limit=1)

    assert len(logs) == 1


def test_list_audit_logs_applies_offset(db_session: Session) -> None:
    older, middle, newest = _seed_logs(db_session)

    logs = list_audit_logs(db_session, offset=1)

    assert logs == [middle, older]
    assert newest not in logs


def test_list_audit_logs_rejects_limit_less_than_one(db_session: Session) -> None:
    with pytest.raises(AuditQueryBusinessRuleError):
        list_audit_logs(db_session, limit=0)


def test_list_audit_logs_caps_limit_greater_than_500(db_session: Session) -> None:
    for _index in range(501):
        _create_audit_log(db_session)

    logs = list_audit_logs(db_session, limit=1000)

    assert len(logs) == 500


def test_list_audit_logs_rejects_negative_offset(db_session: Session) -> None:
    with pytest.raises(AuditQueryBusinessRuleError):
        list_audit_logs(db_session, offset=-1)
