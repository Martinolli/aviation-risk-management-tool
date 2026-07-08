import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
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
from app.models.report import GeneratedReport
from app.models.user import User
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


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Audit Reader",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _governance_reader(db_session: Session) -> User:
    user = _create_user(db_session)
    committee = Committee(
        name=f"Governance {uuid.uuid4()}",
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        is_fixed=True,
        is_active=True,
    )
    db_session.add(committee)
    db_session.flush()
    db_session.add(
        CommitteeMember(committee_id=committee.id, user_id=user.id, is_active=True)
    )
    db_session.flush()
    return user


def _create_committee(
    db_session: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_fixed: bool = False,
    is_active: bool = True,
) -> Committee:
    committee_type = {
        AuthorityLevel.LOW: CommitteeType.OPERATIONAL_BOARD,
        AuthorityLevel.MIDDLE: CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        AuthorityLevel.HIGH: CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE,
    }[authority_level]
    committee = Committee(
        name=f"{authority_level.value} Committee {uuid.uuid4()}",
        authority_level=authority_level,
        committee_type=committee_type,
        is_fixed=is_fixed,
        is_active=is_active,
    )
    db_session.add(committee)
    db_session.flush()
    return committee


def _create_membership(
    db_session: Session,
    *,
    committee: Committee,
    user: User,
    is_active: bool = True,
) -> CommitteeMember:
    membership = CommitteeMember(
        committee_id=committee.id,
        user_id=user.id,
        is_active=is_active,
    )
    db_session.add(membership)
    db_session.flush()
    return membership


def _create_risk_record(
    db_session: Session,
    *,
    creator: User,
    owner: User | None = None,
    board: Committee | None = None,
) -> RiskRecord:
    risk_record = RiskRecord(
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id,
        owner_user_id=owner.id if owner is not None else None,
        board_of_origin_id=board.id if board is not None else None,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


@pytest.fixture()
def reader(db_session: Session) -> User:
    return _governance_reader(db_session)


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


def test_get_audit_log_returns_existing_audit_log(
    db_session: Session, reader: User
) -> None:
    audit_log = _create_audit_log(db_session)

    assert get_audit_log(
        db_session, audit_log_id=audit_log.id, requested_by_user_id=reader.id
    ) is audit_log


def test_get_audit_log_returns_none_for_unknown_audit_log(
    db_session: Session, reader: User
) -> None:
    assert get_audit_log(
        db_session, audit_log_id=uuid.uuid4(), requested_by_user_id=reader.id
    ) is None


def test_list_audit_logs_returns_logs_ordered_by_changed_at_descending(
    db_session: Session, reader: User
) -> None:
    older, middle, newest = _seed_logs(db_session)

    logs = list_audit_logs(db_session, requested_by_user_id=reader.id)

    assert logs == [newest, middle, older]


def test_list_audit_logs_filters_by_entity_type(db_session: Session, reader: User) -> None:
    _seed_logs(db_session)

    logs = list_audit_logs(
        db_session, requested_by_user_id=reader.id, entity_type="RiskRecord"
    )

    assert len(logs) == 1
    assert logs[0].entity_type == "RiskRecord"


def test_list_audit_logs_filters_by_entity_id(db_session: Session, reader: User) -> None:
    target_entity_id = uuid.uuid4()
    target = _create_audit_log(db_session, entity_id=target_entity_id)
    _create_audit_log(db_session)

    logs = list_audit_logs(
        db_session, requested_by_user_id=reader.id, entity_id=target_entity_id
    )

    assert logs == [target]


def test_list_audit_logs_filters_by_action(db_session: Session, reader: User) -> None:
    _seed_logs(db_session)

    logs = list_audit_logs(
        db_session, requested_by_user_id=reader.id, action=AuditAction.UPDATE
    )

    assert len(logs) == 1
    assert logs[0].action == AuditAction.UPDATE


def test_list_audit_logs_filters_by_changed_by_user_id(
    db_session: Session, reader: User
) -> None:
    user_id = uuid.uuid4()
    target = _create_audit_log(db_session, changed_by_user_id=user_id)
    _create_audit_log(db_session, changed_by_user_id=uuid.uuid4())

    logs = list_audit_logs(
        db_session, requested_by_user_id=reader.id, changed_by_user_id=user_id
    )

    assert logs == [target]


def test_list_audit_logs_filters_by_changed_at_range(
    db_session: Session, reader: User
) -> None:
    now = datetime.now(timezone.utc)
    older = _create_audit_log(db_session, changed_at=now - timedelta(days=2))
    middle = _create_audit_log(db_session, changed_at=now - timedelta(days=1))
    newer = _create_audit_log(db_session, changed_at=now)

    logs = list_audit_logs(
        db_session,
        requested_by_user_id=reader.id,
        changed_at_from=now - timedelta(days=1, hours=1),
        changed_at_to=now - timedelta(hours=1),
    )

    assert logs == [middle]
    assert older not in logs
    assert newer not in logs


def test_list_audit_logs_applies_limit(db_session: Session, reader: User) -> None:
    _seed_logs(db_session)

    logs = list_audit_logs(db_session, requested_by_user_id=reader.id, limit=1)

    assert len(logs) == 1


def test_list_audit_logs_applies_offset(db_session: Session, reader: User) -> None:
    older, middle, newest = _seed_logs(db_session)

    logs = list_audit_logs(db_session, requested_by_user_id=reader.id, offset=1)

    assert logs == [middle, older]
    assert newest not in logs


def test_list_audit_logs_rejects_limit_less_than_one(
    db_session: Session, reader: User
) -> None:
    with pytest.raises(AuditQueryBusinessRuleError):
        list_audit_logs(db_session, requested_by_user_id=reader.id, limit=0)


def test_list_audit_logs_caps_limit_greater_than_500(
    db_session: Session, reader: User
) -> None:
    for _index in range(501):
        _create_audit_log(db_session)

    logs = list_audit_logs(db_session, requested_by_user_id=reader.id, limit=1000)

    assert len(logs) == 500


def test_list_audit_logs_rejects_negative_offset(
    db_session: Session, reader: User
) -> None:
    with pytest.raises(AuditQueryBusinessRuleError):
        list_audit_logs(db_session, requested_by_user_id=reader.id, offset=-1)


def test_audit_queries_require_an_active_reader(db_session: Session) -> None:
    audit_log = _create_audit_log(db_session)
    inactive_user = _create_user(db_session, is_active=False)

    for user_id, message in [
        (None, "authenticated active user"),
        (uuid.uuid4(), "user does not exist"),
        (inactive_user.id, "user is inactive"),
    ]:
        with pytest.raises(AuditQueryBusinessRuleError, match=message):
            list_audit_logs(db_session, requested_by_user_id=user_id)
        with pytest.raises(AuditQueryBusinessRuleError, match=message):
            get_audit_log(
                db_session,
                audit_log_id=audit_log.id,
                requested_by_user_id=user_id,
            )


def test_risk_record_audit_access_allows_related_users_and_filters_others(
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    board_member = _create_user(db_session)
    governance_member = _governance_reader(db_session)
    unrelated_user = _create_user(db_session)
    board = _create_committee(db_session)
    _create_membership(db_session, committee=board, user=board_member)
    risk_record = _create_risk_record(
        db_session,
        creator=creator,
        owner=owner,
        board=board,
    )
    audit_log = _create_audit_log(
        db_session,
        entity_type="RiskRecord",
        entity_id=risk_record.id,
    )

    for user in (creator, owner, board_member, governance_member):
        assert get_audit_log(
            db_session,
            audit_log_id=audit_log.id,
            requested_by_user_id=user.id,
        ) is audit_log
    assert list_audit_logs(
        db_session,
        requested_by_user_id=unrelated_user.id,
        entity_type="RiskRecord",
    ) == []
    with pytest.raises(AuditQueryBusinessRuleError, match="not authorized"):
        get_audit_log(
            db_session,
            audit_log_id=audit_log.id,
            requested_by_user_id=unrelated_user.id,
        )


def test_child_entity_audit_access_allows_entity_and_risk_relationships(
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    assessor = _create_user(db_session)
    action_owner = _create_user(db_session)
    decision_maker = _create_user(db_session)
    committee_member = _create_user(db_session)
    report_generator = _create_user(db_session)
    unrelated_user = _create_user(db_session)
    committee = _create_committee(db_session)
    _create_membership(db_session, committee=committee, user=committee_member)
    risk_record = _create_risk_record(db_session, creator=creator)
    assessment = RiskAssessment(
        risk_record_id=risk_record.id,
        assessment_type=RiskAssessmentType.INITIAL,
        severity="Major",
        likelihood="Remote",
        risk_level="Medium",
        assessed_by_user_id=assessor.id,
        assessed_at=datetime.now(timezone.utc),
    )
    action = RiskAction(
        risk_record_id=risk_record.id,
        title="Action",
        status=RiskActionStatus.OPEN,
        action_owner_user_id=action_owner.id,
    )
    decision = RiskDecision(
        risk_record_id=risk_record.id,
        committee_id=committee.id,
        decision_type=RiskDecisionType.APPROVE,
        decision_text="Approved",
        decided_by_user_id=decision_maker.id,
        decided_at=datetime.now(timezone.utc),
    )
    report = GeneratedReport(
        risk_record_id=risk_record.id,
        report_type="RISK_DOSSIER_DOCX",
        file_path="report.docx",
        generated_by_user_id=report_generator.id,
        generated_at=datetime.now(timezone.utc),
        template_version="1.0",
    )
    db_session.add_all([assessment, action, decision, report])
    db_session.flush()
    logs = {
        "assessment": _create_audit_log(
            db_session, entity_type="RiskAssessment", entity_id=assessment.id
        ),
        "action": _create_audit_log(
            db_session, entity_type="RiskAction", entity_id=action.id
        ),
        "decision": _create_audit_log(
            db_session, entity_type="RiskDecision", entity_id=decision.id
        ),
        "report": _create_audit_log(
            db_session, entity_type="GeneratedReport", entity_id=report.id
        ),
    }

    for audit_log, user in [
        (logs["assessment"], assessor),
        (logs["action"], action_owner),
        (logs["decision"], decision_maker),
        (logs["decision"], committee_member),
        (logs["report"], report_generator),
        (logs["report"], creator),
    ]:
        assert get_audit_log(
            db_session,
            audit_log_id=audit_log.id,
            requested_by_user_id=user.id,
        ) is audit_log
    with pytest.raises(AuditQueryBusinessRuleError, match="not authorized"):
        get_audit_log(
            db_session,
            audit_log_id=logs["action"].id,
            requested_by_user_id=unrelated_user.id,
        )


def test_administrative_and_unknown_audit_logs_require_governance_or_self(
    db_session: Session,
) -> None:
    governance_member = _governance_reader(db_session)
    user = _create_user(db_session)
    low_member = _create_user(db_session)
    low_committee = _create_committee(db_session)
    membership = _create_membership(db_session, committee=low_committee, user=low_member)
    user_log = _create_audit_log(db_session, entity_type="User", entity_id=user.id)
    membership_log = _create_audit_log(
        db_session, entity_type="CommitteeMember", entity_id=membership.id
    )
    unknown_log = _create_audit_log(db_session, entity_type="Unknown", entity_id=uuid.uuid4())
    unlinked_report = GeneratedReport(
        report_type="RISK_DOSSIER_DOCX",
        file_path="unlinked.docx",
        generated_by_user_id=low_member.id,
        generated_at=datetime.now(timezone.utc),
        template_version="1.0",
    )
    db_session.add(unlinked_report)
    db_session.flush()
    unlinked_report_log = _create_audit_log(
        db_session,
        entity_type="GeneratedReport",
        entity_id=unlinked_report.id,
    )

    assert get_audit_log(
        db_session, audit_log_id=user_log.id, requested_by_user_id=user.id
    ) is user_log
    assert get_audit_log(
        db_session,
        audit_log_id=membership_log.id,
        requested_by_user_id=low_member.id,
    ) is membership_log
    for audit_log in (user_log, membership_log, unknown_log, unlinked_report_log):
        assert get_audit_log(
            db_session,
            audit_log_id=audit_log.id,
            requested_by_user_id=governance_member.id,
        ) is audit_log
    with pytest.raises(AuditQueryBusinessRuleError, match="not authorized"):
        get_audit_log(
            db_session,
            audit_log_id=unknown_log.id,
            requested_by_user_id=low_member.id,
        )
    with pytest.raises(AuditQueryBusinessRuleError, match="not authorized"):
        get_audit_log(
            db_session,
            audit_log_id=unlinked_report_log.id,
            requested_by_user_id=low_member.id,
        )
