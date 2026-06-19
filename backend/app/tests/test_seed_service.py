import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee
from app.models.enums import AuditAction, AuthorityLevel, CommitteeType
from app.services.seed_service import (
    DEFAULT_GOVERNANCE_COMMITTEES,
    get_default_committee_names,
    seed_default_committees,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("seed service must not commit transactions")


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


def test_seed_default_committees_creates_exactly_five_default_committees(
    db_session: Session,
) -> None:
    committees = seed_default_committees(db_session)
    saved_count = db_session.scalar(select(func.count()).select_from(Committee))

    assert len(committees) == 5
    assert saved_count == 5
    assert {committee.name for committee in committees} == set(
        get_default_committee_names()
    )


def test_low_default_committees_are_not_fixed(db_session: Session) -> None:
    committees = seed_default_committees(db_session)

    low_committees = [
        committee
        for committee in committees
        if committee.authority_level == AuthorityLevel.LOW
    ]

    assert len(low_committees) == 3
    assert all(
        committee.committee_type == CommitteeType.OPERATIONAL_BOARD
        for committee in low_committees
    )
    assert all(committee.is_fixed is False for committee in low_committees)
    assert all(committee.is_active is True for committee in low_committees)


def test_middle_default_committee_is_fixed(db_session: Session) -> None:
    committees = seed_default_committees(db_session)

    middle_committee = next(
        committee
        for committee in committees
        if committee.authority_level == AuthorityLevel.MIDDLE
    )

    assert middle_committee.name == "Risk Management Committee"
    assert middle_committee.committee_type == CommitteeType.RISK_MANAGEMENT_COMMITTEE
    assert middle_committee.is_fixed is True
    assert middle_committee.is_active is True


def test_high_default_committee_is_fixed(db_session: Session) -> None:
    committees = seed_default_committees(db_session)

    high_committee = next(
        committee
        for committee in committees
        if committee.authority_level == AuthorityLevel.HIGH
    )

    assert high_committee.name == "Executive Safety Management Committee"
    assert (
        high_committee.committee_type
        == CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE
    )
    assert high_committee.is_fixed is True
    assert high_committee.is_active is True


def test_seed_default_committees_twice_does_not_create_duplicates(
    db_session: Session,
) -> None:
    first_seed = seed_default_committees(db_session)
    second_seed = seed_default_committees(db_session)

    saved_count = db_session.scalar(select(func.count()).select_from(Committee))

    assert saved_count == 5
    assert {committee.id for committee in first_seed} == {
        committee.id for committee in second_seed
    }


def test_seed_creates_audit_log_records_for_new_committees(
    db_session: Session,
) -> None:
    committees = seed_default_committees(db_session)

    audit_logs = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == AuditAction.CREATE,
                AuditLog.entity_type == "Committee",
            )
        )
    )

    assert len(audit_logs) == 5
    assert {audit_log.entity_id for audit_log in audit_logs} == {
        committee.id for committee in committees
    }


def test_seed_does_not_create_audit_logs_for_existing_committees(
    db_session: Session,
) -> None:
    seed_default_committees(db_session)
    seed_default_committees(db_session)

    audit_log_count = db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.action == AuditAction.CREATE,
            AuditLog.entity_type == "Committee",
        )
    )

    assert audit_log_count == 5


def test_existing_committees_are_not_overwritten_by_seed(db_session: Session) -> None:
    existing_name = DEFAULT_GOVERNANCE_COMMITTEES[0]["name"]
    existing_committee = Committee(
        name=existing_name,
        description="Custom existing description",
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        is_fixed=True,
        is_active=False,
    )
    db_session.add(existing_committee)
    db_session.flush()
    existing_committee_id = existing_committee.id

    committees = seed_default_committees(db_session)
    returned_existing = next(
        committee for committee in committees if committee.name == existing_name
    )

    assert returned_existing.id == existing_committee_id
    assert returned_existing.description == "Custom existing description"
    assert returned_existing.authority_level == AuthorityLevel.MIDDLE
    assert returned_existing.committee_type == CommitteeType.RISK_MANAGEMENT_COMMITTEE
    assert returned_existing.is_fixed is True
    assert returned_existing.is_active is False


def test_returned_list_contains_the_five_default_committees(db_session: Session) -> None:
    committees = seed_default_committees(
        db_session,
        changed_by_user_id=uuid.uuid4(),
    )

    assert len(committees) == 5
    assert [committee.name for committee in committees] == get_default_committee_names()
