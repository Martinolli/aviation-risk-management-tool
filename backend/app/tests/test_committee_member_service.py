import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee
from app.models.enums import AuditAction, AuthorityLevel, CommitteeType
from app.models.user import User
from app.schemas.committee_member import CommitteeMemberCreate, CommitteeMemberUpdate
from app.services.committee_member_service import (
    CommitteeMemberBusinessRuleError,
    create_committee_member,
    get_committee_member,
    list_committee_members,
    update_committee_member,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("committee member service must not commit transactions")


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


def _committee(db: Session, *, is_active: bool = True) -> Committee:
    committee = Committee(
        name=f"Committee {uuid.uuid4()}",
        authority_level=AuthorityLevel.LOW,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_active=is_active,
    )
    db.add(committee)
    db.flush()
    return committee


def _user(db: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Committee User",
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def _data(committee: Committee, user: User, role_label: str | None = "Chair") -> CommitteeMemberCreate:
    return CommitteeMemberCreate(
        committee_id=committee.id,
        user_id=user.id,
        role_label=role_label,
    )


def test_create_member_succeeds_and_writes_audit_log(db_session: Session) -> None:
    member = create_committee_member(db_session, data=_data(_committee(db_session), _user(db_session)))

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == member.id,
            AuditLog.action == AuditAction.CREATE,
        )
    )
    assert member.is_active is True
    assert audit_log is not None


def test_create_member_validates_committee_user_duplicate_and_role_label(
    db_session: Session,
) -> None:
    committee = _committee(db_session)
    user = _user(db_session)
    with pytest.raises(CommitteeMemberBusinessRuleError):
        create_committee_member(db_session, data=_data(_committee(db_session, is_active=False), user))
    with pytest.raises(CommitteeMemberBusinessRuleError):
        create_committee_member(db_session, data=_data(committee, _user(db_session, is_active=False)))
    with pytest.raises(CommitteeMemberBusinessRuleError):
        create_committee_member(
            db_session,
            data=CommitteeMemberCreate(committee_id=uuid.uuid4(), user_id=user.id),
        )
    with pytest.raises(CommitteeMemberBusinessRuleError):
        create_committee_member(
            db_session,
            data=CommitteeMemberCreate(committee_id=committee.id, user_id=uuid.uuid4()),
        )
    with pytest.raises(CommitteeMemberBusinessRuleError):
        create_committee_member(db_session, data=_data(committee, user, "   "))

    create_committee_member(db_session, data=_data(committee, user))
    with pytest.raises(CommitteeMemberBusinessRuleError):
        create_committee_member(db_session, data=_data(committee, user))


def test_list_filters_and_update_member(db_session: Session) -> None:
    first_committee, second_committee = _committee(db_session), _committee(db_session)
    first_user, second_user = _user(db_session), _user(db_session)
    first_member = create_committee_member(db_session, data=_data(first_committee, first_user))
    create_committee_member(db_session, data=_data(second_committee, second_user))
    updated_member = update_committee_member(
        db_session,
        committee_member_id=first_member.id,
        data=CommitteeMemberUpdate(role_label="Secretary"),
    )
    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == first_member.id,
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "role_label",
        )
    )
    assert get_committee_member(db_session, committee_member_id=uuid.uuid4()) is None
    assert list_committee_members(db_session, committee_id=first_committee.id) == [first_member]
    assert list_committee_members(db_session, user_id=first_user.id) == [first_member]
    assert updated_member.role_label == "Secretary"
    assert audit_log is not None
    with pytest.raises(CommitteeMemberBusinessRuleError):
        update_committee_member(
            db_session,
            committee_member_id=first_member.id,
            data=CommitteeMemberUpdate(role_label="   "),
        )

    update_committee_member(
        db_session, committee_member_id=first_member.id, data=CommitteeMemberUpdate(is_active=False)
    )
    assert first_member not in list_committee_members(db_session)
    assert first_member in list_committee_members(db_session, include_inactive=True)
