import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import AuditAction
from app.schemas.role import RoleCreate, RoleUpdate
from app.services.role_service import (
    RoleBusinessRuleError,
    create_role,
    get_role,
    list_roles,
    update_role,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("role service must not commit transactions")


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


def test_create_role_succeeds_and_writes_audit_log(db_session: Session) -> None:
    role = create_role(db_session, data=RoleCreate(name="Chair", description="Leads"))

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == role.id,
            AuditLog.action == AuditAction.CREATE,
        )
    )
    assert role.name == "Chair"
    assert audit_log is not None


def test_create_role_rejects_duplicate_and_blank_names(db_session: Session) -> None:
    create_role(db_session, data=RoleCreate(name="Chair"))
    with pytest.raises(RoleBusinessRuleError):
        create_role(db_session, data=RoleCreate(name="chair"))
    with pytest.raises(RoleBusinessRuleError):
        create_role(db_session, data=RoleCreate(name="   "))


def test_get_list_and_update_role(db_session: Session) -> None:
    role = create_role(db_session, data=RoleCreate(name="Chair"))
    updated_role = update_role(
        db_session,
        role_id=role.id,
        data=RoleUpdate(description="Committee chair"),
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == role.id,
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "description",
        )
    )
    assert get_role(db_session, role_id=role.id) is role
    assert get_role(db_session, role_id=uuid.uuid4()) is None
    assert list_roles(db_session) == [role]
    assert updated_role.description == "Committee chair"
    assert audit_log is not None
