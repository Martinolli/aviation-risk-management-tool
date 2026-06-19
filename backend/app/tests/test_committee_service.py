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
from app.schemas.committee import CommitteeCreate, CommitteeUpdate
from app.services.committee_service import (
    CommitteeBusinessRuleError,
    archive_committee,
    create_committee,
    list_committees,
    update_committee,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("committee service must not commit transactions")


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


def _name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _create_fixed_committee(
    db_session: Session,
    *,
    name: str,
    authority_level: AuthorityLevel,
    committee_type: CommitteeType,
) -> Committee:
    committee = Committee(
        name=name,
        authority_level=authority_level,
        committee_type=committee_type,
        is_fixed=True,
        is_active=True,
    )
    db_session.add(committee)
    db_session.flush()
    return committee


def test_create_low_operational_board_committee_succeeds(
    db_session: Session,
) -> None:
    committee = create_committee(
        db_session,
        data=CommitteeCreate(
            name=_name("Flight Test Safety Committee"),
            description="Operational board",
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
        ),
    )

    assert committee.id is not None
    assert committee.authority_level == AuthorityLevel.LOW
    assert committee.committee_type == CommitteeType.OPERATIONAL_BOARD
    assert committee.is_fixed is False


@pytest.mark.parametrize("authority_level", [AuthorityLevel.MIDDLE, AuthorityLevel.HIGH])
def test_create_non_low_committee_raises_business_rule_error(
    db_session: Session,
    authority_level: AuthorityLevel,
) -> None:
    with pytest.raises(CommitteeBusinessRuleError):
        create_committee(
            db_session,
            data=CommitteeCreate(
                name=_name("Protected Committee"),
                description=None,
                authority_level=authority_level,
                committee_type=CommitteeType.OPERATIONAL_BOARD,
            ),
        )


def test_create_non_operational_board_committee_raises_business_rule_error(
    db_session: Session,
) -> None:
    with pytest.raises(CommitteeBusinessRuleError):
        create_committee(
            db_session,
            data=CommitteeCreate(
                name=_name("Risk Management Committee"),
                description=None,
                authority_level=AuthorityLevel.LOW,
                committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
            ),
        )


def test_update_low_committee_name_succeeds_and_creates_audit_log(
    db_session: Session,
) -> None:
    committee = create_committee(
        db_session,
        data=CommitteeCreate(
            name=_name("Industrial Safety Committee"),
            description=None,
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
        ),
    )
    old_name = committee.name
    new_name = _name("Industrial Safety Board")

    updated_committee = update_committee(
        db_session,
        committee_id=committee.id,
        data=CommitteeUpdate(name=new_name),
    )

    audit_log = db_session.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity_id == committee.id,
            AuditLog.action == AuditAction.UPDATE,
            AuditLog.field_name == "name",
        )
        .order_by(AuditLog.changed_at.desc())
    )

    assert updated_committee.name == new_name
    assert audit_log is not None
    assert audit_log.old_value == old_name
    assert audit_log.new_value == new_name


def test_update_fixed_committee_name_raises_business_rule_error(
    db_session: Session,
) -> None:
    committee = _create_fixed_committee(
        db_session,
        name=_name("Risk Management Committee"),
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
    )

    with pytest.raises(CommitteeBusinessRuleError):
        update_committee(
            db_session,
            committee_id=committee.id,
            data=CommitteeUpdate(name=_name("Renamed Committee")),
        )


def test_archive_low_non_fixed_committee_succeeds_and_creates_audit_log(
    db_session: Session,
) -> None:
    committee = create_committee(
        db_session,
        data=CommitteeCreate(
            name=_name("Aircraft Safety Committee"),
            description=None,
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
        ),
    )

    archived_committee = archive_committee(
        db_session,
        committee_id=committee.id,
        archive_reason="No longer needed",
    )

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == committee.id,
            AuditLog.action == AuditAction.ARCHIVE,
        )
    )

    assert archived_committee.is_active is False
    assert archived_committee.archived_at is not None
    assert archived_committee.archive_reason == "No longer needed"
    assert audit_log is not None
    assert audit_log.reason == "No longer needed"


@pytest.mark.parametrize(
    ("authority_level", "committee_type"),
    [
        (AuthorityLevel.MIDDLE, CommitteeType.RISK_MANAGEMENT_COMMITTEE),
        (AuthorityLevel.HIGH, CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE),
    ],
)
def test_archive_fixed_committee_raises_business_rule_error(
    db_session: Session,
    authority_level: AuthorityLevel,
    committee_type: CommitteeType,
) -> None:
    committee = _create_fixed_committee(
        db_session,
        name=_name("Fixed Committee"),
        authority_level=authority_level,
        committee_type=committee_type,
    )

    with pytest.raises(CommitteeBusinessRuleError):
        archive_committee(
            db_session,
            committee_id=committee.id,
            archive_reason="Attempted archive",
        )


def test_list_committees_excludes_archived_committees_by_default(
    db_session: Session,
) -> None:
    active_committee = create_committee(
        db_session,
        data=CommitteeCreate(
            name=_name("Active Board"),
            description=None,
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
        ),
    )
    archived_committee = create_committee(
        db_session,
        data=CommitteeCreate(
            name=_name("Archived Board"),
            description=None,
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
        ),
    )
    archive_committee(
        db_session,
        committee_id=archived_committee.id,
        archive_reason="Archived for test",
    )

    committees = list_committees(db_session)

    assert active_committee in committees
    assert archived_committee not in committees


def test_list_committees_includes_archived_committees_when_requested(
    db_session: Session,
) -> None:
    active_committee = create_committee(
        db_session,
        data=CommitteeCreate(
            name=_name("Active Board"),
            description=None,
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
        ),
    )
    archived_committee = create_committee(
        db_session,
        data=CommitteeCreate(
            name=_name("Archived Board"),
            description=None,
            authority_level=AuthorityLevel.LOW,
            committee_type=CommitteeType.OPERATIONAL_BOARD,
        ),
    )
    archive_committee(
        db_session,
        committee_id=archived_committee.id,
        archive_reason="Archived for test",
    )

    committees = list_committees(db_session, include_archived=True)

    assert active_committee in committees
    assert archived_committee in committees
