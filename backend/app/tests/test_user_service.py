import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import AuditAction
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import (
    UserBusinessRuleError,
    create_user,
    get_user,
    list_users,
    update_user,
)
from app.services.security_service import verify_password


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("user service must not commit transactions")


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine, class_=NoCommitSession)() as session:
        yield session
    Base.metadata.drop_all(engine)


def _data(
    email: str | None = None,
    display_name: str = "Avery Pilot",
    password: str | None = None,
) -> UserCreate:
    return UserCreate(
        email=email or f"{uuid.uuid4()}@example.com",
        display_name=display_name,
        password=password,
    )


def test_create_user_succeeds_is_active_and_writes_audit_log(db_session: Session) -> None:
    user = create_user(db_session, data=_data())

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == user.id,
            AuditLog.action == AuditAction.CREATE,
        )
    )
    assert user.is_active is True
    assert audit_log is not None
    assert user.password_hash is None


def test_create_and_update_user_password_hashes_and_audits_safely(
    db_session: Session,
) -> None:
    old_password = "StrongPassword123!"
    new_password = "NewStrongPassword456!"
    user = create_user(db_session, data=_data(password=old_password))

    assert user.password_hash is not None
    assert user.password_hash != old_password
    assert verify_password(old_password, user.password_hash)

    update_user(
        db_session,
        user_id=user.id,
        data=UserUpdate(password=new_password),
    )
    password_audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == user.id,
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "password",
        )
    )

    assert verify_password(new_password, user.password_hash)
    assert not verify_password(old_password, user.password_hash)
    assert password_audit_log is not None
    assert password_audit_log.new_value == "***UPDATED***"
    assert old_password not in str(password_audit_log.new_value)
    assert new_password not in str(password_audit_log.new_value)
    assert user.password_hash not in str(password_audit_log.new_value)


def test_update_user_with_null_password_does_not_clear_existing_password(
    db_session: Session,
) -> None:
    password = "StrongPassword123!"
    user = create_user(db_session, data=_data(password=password))
    original_hash = user.password_hash

    update_user(db_session, user_id=user.id, data=UserUpdate(password=None))

    assert user.password_hash == original_hash


def test_create_user_rejects_duplicate_email_case_insensitively(db_session: Session) -> None:
    create_user(db_session, data=_data("Avery@example.com"))

    with pytest.raises(UserBusinessRuleError):
        create_user(db_session, data=_data("avery@EXAMPLE.com"))


@pytest.mark.parametrize("display_name", ["   "])
def test_create_user_rejects_empty_display_name(
    db_session: Session, display_name: str
) -> None:
    with pytest.raises(UserBusinessRuleError):
        create_user(db_session, data=_data(display_name=display_name))


def test_get_user_and_list_users_respect_active_filter(db_session: Session) -> None:
    active_user = create_user(db_session, data=_data(display_name="Active User"))
    inactive_user = create_user(db_session, data=_data(display_name="Inactive User"))
    update_user(db_session, user_id=inactive_user.id, data=UserUpdate(is_active=False))

    assert get_user(db_session, user_id=active_user.id) is active_user
    assert get_user(db_session, user_id=uuid.uuid4()) is None
    assert list_users(db_session) == [active_user]
    assert set(list_users(db_session, include_inactive=True)) == {active_user, inactive_user}


def test_update_user_writes_update_audit_log_and_rejects_blank_name(
    db_session: Session,
) -> None:
    user = create_user(db_session, data=_data())
    updated_user = update_user(
        db_session,
        user_id=user.id,
        data=UserUpdate(display_name="Avery Test Pilot"),
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == user.id,
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "display_name",
        )
    )
    assert updated_user.display_name == "Avery Test Pilot"
    assert audit_log is not None
    with pytest.raises(UserBusinessRuleError):
        update_user(db_session, user_id=user.id, data=UserUpdate(display_name="   "))
