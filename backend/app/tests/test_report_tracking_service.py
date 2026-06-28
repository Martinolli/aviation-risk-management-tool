import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
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
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.report import GeneratedReport
from app.models.risk import RiskRecord
from app.models.user import User
from app.services.report_tracking_service import (
    GeneratedReportNotFoundError,
    RISK_DOSSIER_REPORT_TYPE,
    ReportTrackingBusinessRuleError,
    generate_and_track_risk_dossier_report,
    get_authorized_generated_report,
    get_authorized_generated_report_file_path,
    get_generated_report,
    get_generated_report_file_path,
    list_authorized_generated_reports,
    list_generated_reports,
)


class NoCommitSession(Session):
    def commit(self) -> None:
        raise AssertionError("report tracking service must not commit transactions")


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
    risk_id: str = "RISK-2026-0001",
    creator: User | None = None,
    owner: User | None = None,
    board_of_origin_id: uuid.UUID | None = None,
) -> RiskRecord:
    creator = creator or _create_user(db_session)
    risk_record = RiskRecord(
        risk_id=risk_id,
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id,
        owner_user_id=owner.id if owner is not None else None,
        board_of_origin_id=board_of_origin_id,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


def _create_user(db_session: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        display_name="Report User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_committee(
    db_session: Session,
    *,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    is_active: bool = True,
    is_fixed: bool = False,
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
        is_active=is_active,
        is_fixed=is_fixed,
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


def _generate_report(
    db_session: Session,
    tmp_path: Path,
    *,
    risk_record: RiskRecord | None = None,
    generated_by_user_id: uuid.UUID | None = None,
) -> GeneratedReport:
    risk_record = risk_record or _create_risk_record(db_session)
    return generate_and_track_risk_dossier_report(
        db_session,
        risk_record_id=risk_record.id,
        output_dir=tmp_path,
        generated_by_user_id=(
            generated_by_user_id
            if generated_by_user_id is not None
            else risk_record.created_by_user_id
        ),
    )


def test_generate_and_track_risk_dossier_report_creates_docx_file(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    assert Path(generated_report.file_path).exists()
    assert generated_report.file_path.endswith(".docx")


def test_generate_report_requires_active_actor(db_session: Session, tmp_path: Path) -> None:
    risk_record = _create_risk_record(db_session)
    inactive_user = _create_user(db_session, is_active=False)

    with pytest.raises(ReportTrackingBusinessRuleError, match="authenticated active user"):
        generate_and_track_risk_dossier_report(
            db_session, risk_record_id=risk_record.id, output_dir=tmp_path
        )
    with pytest.raises(ReportTrackingBusinessRuleError, match="user does not exist"):
        generate_and_track_risk_dossier_report(
            db_session,
            risk_record_id=risk_record.id,
            output_dir=tmp_path,
            generated_by_user_id=uuid.uuid4(),
        )
    with pytest.raises(ReportTrackingBusinessRuleError, match="user is inactive"):
        generate_and_track_risk_dossier_report(
            db_session,
            risk_record_id=risk_record.id,
            output_dir=tmp_path,
            generated_by_user_id=inactive_user.id,
        )


def test_report_generation_authorizes_creator_owner_board_and_governance_members(
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    board_member = _create_user(db_session)
    middle_member = _create_user(db_session)
    high_member = _create_user(db_session)
    board = _create_committee(db_session)
    middle_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.MIDDLE,
        is_fixed=True,
    )
    high_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.HIGH,
        is_fixed=True,
    )
    _create_membership(db_session, committee=board, user=board_member)
    _create_membership(db_session, committee=middle_committee, user=middle_member)
    _create_membership(db_session, committee=high_committee, user=high_member)
    risk_record = _create_risk_record(
        db_session,
        creator=creator,
        owner=owner,
        board_of_origin_id=board.id,
    )

    reports = [
        _generate_report(
            db_session,
            tmp_path,
            risk_record=risk_record,
            generated_by_user_id=user.id,
        )
        for user in (creator, owner, board_member, middle_member, high_member)
    ]

    assert [report.generated_by_user_id for report in reports] == [
        creator.id,
        owner.id,
        board_member.id,
        middle_member.id,
        high_member.id,
    ]


def test_report_generation_rejects_unrelated_or_inactive_memberships(
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    unrelated_user = _create_user(db_session)
    board_member_with_inactive_membership = _create_user(db_session)
    inactive_committee_member = _create_user(db_session)
    low_committee_member = _create_user(db_session)
    board = _create_committee(db_session)
    inactive_committee = _create_committee(db_session, is_active=False)
    unrelated_low_committee = _create_committee(db_session)
    _create_membership(
        db_session,
        committee=board,
        user=board_member_with_inactive_membership,
        is_active=False,
    )
    _create_membership(
        db_session,
        committee=inactive_committee,
        user=inactive_committee_member,
    )
    _create_membership(
        db_session,
        committee=unrelated_low_committee,
        user=low_committee_member,
    )
    risk_record = _create_risk_record(
        db_session,
        creator=creator,
        board_of_origin_id=board.id,
    )

    for user in (
        unrelated_user,
        board_member_with_inactive_membership,
        inactive_committee_member,
        low_committee_member,
    ):
        with pytest.raises(ReportTrackingBusinessRuleError, match="not authorized"):
            _generate_report(
                db_session,
                tmp_path,
                risk_record=risk_record,
                generated_by_user_id=user.id,
            )


def test_generate_and_track_risk_dossier_report_creates_generated_report_row(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    saved_report = db_session.get(GeneratedReport, generated_report.id)

    assert saved_report is generated_report


def test_generated_report_has_risk_dossier_report_type(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    assert generated_report.report_type == "RISK_DOSSIER_DOCX"


def test_generated_report_file_path_points_to_existing_file(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    assert Path(generated_report.file_path).is_file()


def test_generate_report_for_unknown_risk_raises_business_rule_error(
    db_session: Session,
    tmp_path: Path,
) -> None:
    with pytest.raises(ReportTrackingBusinessRuleError):
        generate_and_track_risk_dossier_report(
            db_session,
            risk_record_id=uuid.uuid4(),
            output_dir=tmp_path,
        )


def test_generate_report_writes_generate_report_audit_log(
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    generated_report = _generate_report(db_session, tmp_path, risk_record=risk_record)

    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk_record.id,
            AuditLog.entity_type == "RiskRecord",
            AuditLog.action == AuditAction.GENERATE_REPORT,
        )
    )

    assert audit_log is not None
    assert audit_log.new_value["report_id"] == str(generated_report.id)
    assert audit_log.changed_by_user_id == generated_report.generated_by_user_id


def test_get_generated_report_returns_existing_report(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    assert get_generated_report(
        db_session,
        generated_report_id=generated_report.id,
    ) is generated_report


def test_get_generated_report_returns_none_for_unknown_report(
    db_session: Session,
) -> None:
    assert get_generated_report(db_session, generated_report_id=uuid.uuid4()) is None


def test_get_generated_report_file_path_returns_existing_file(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    assert get_generated_report_file_path(
        db_session,
        generated_report_id=generated_report.id,
    ) == Path(generated_report.file_path)


def test_authorized_report_download_allows_related_users(
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    owner = _create_user(db_session)
    board_member = _create_user(db_session)
    middle_member = _create_user(db_session)
    high_member = _create_user(db_session)
    board = _create_committee(db_session)
    middle_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.MIDDLE,
        is_fixed=True,
    )
    high_committee = _create_committee(
        db_session,
        authority_level=AuthorityLevel.HIGH,
        is_fixed=True,
    )
    _create_membership(db_session, committee=board, user=board_member)
    _create_membership(db_session, committee=middle_committee, user=middle_member)
    _create_membership(db_session, committee=high_committee, user=high_member)
    risk_record = _create_risk_record(
        db_session,
        creator=creator,
        owner=owner,
        board_of_origin_id=board.id,
    )
    generated_report = _generate_report(
        db_session,
        tmp_path,
        risk_record=risk_record,
        generated_by_user_id=creator.id,
    )

    for user in (creator, owner, board_member, middle_member, high_member):
        assert get_authorized_generated_report_file_path(
            db_session,
            generated_report_id=generated_report.id,
            requested_by_user_id=user.id,
        ) == Path(generated_report.file_path)


def test_authorized_report_download_rejects_invalid_or_unrelated_users(
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    unrelated_user = _create_user(db_session)
    inactive_user = _create_user(db_session, is_active=False)
    inactive_board_member = _create_user(db_session)
    inactive_committee_member = _create_user(db_session)
    low_committee_member = _create_user(db_session)
    board = _create_committee(db_session)
    inactive_committee = _create_committee(db_session, is_active=False)
    low_committee = _create_committee(db_session)
    _create_membership(
        db_session,
        committee=board,
        user=inactive_board_member,
        is_active=False,
    )
    _create_membership(
        db_session,
        committee=inactive_committee,
        user=inactive_committee_member,
    )
    _create_membership(db_session, committee=low_committee, user=low_committee_member)
    risk_record = _create_risk_record(
        db_session,
        creator=creator,
        board_of_origin_id=board.id,
    )
    generated_report = _generate_report(
        db_session,
        tmp_path,
        risk_record=risk_record,
        generated_by_user_id=creator.id,
    )

    for user_id, message in [
        (None, "download requires"),
        (uuid.uuid4(), "user does not exist"),
        (inactive_user.id, "user is inactive"),
        (unrelated_user.id, "not authorized to download"),
        (inactive_board_member.id, "not authorized to download"),
        (inactive_committee_member.id, "not authorized to download"),
        (low_committee_member.id, "not authorized to download"),
    ]:
        with pytest.raises(ReportTrackingBusinessRuleError, match=message):
            get_authorized_generated_report_file_path(
                db_session,
                generated_report_id=generated_report.id,
                requested_by_user_id=user_id,
            )


def test_authorized_report_download_validates_report_link_and_file(
    db_session: Session,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    risk_record = _create_risk_record(db_session, creator=creator)
    generated_report = _generate_report(
        db_session,
        tmp_path,
        risk_record=risk_record,
        generated_by_user_id=creator.id,
    )
    generated_report.file_path = str(tmp_path / "missing.docx")

    with pytest.raises(ReportTrackingBusinessRuleError, match="does not exist"):
        get_authorized_generated_report_file_path(
            db_session,
            generated_report_id=generated_report.id,
            requested_by_user_id=creator.id,
        )
    generated_report.file_path = str(tmp_path)
    with pytest.raises(ReportTrackingBusinessRuleError, match="not a file"):
        get_authorized_generated_report_file_path(
            db_session,
            generated_report_id=generated_report.id,
            requested_by_user_id=creator.id,
        )

    unlinked_report = GeneratedReport(
        report_type=RISK_DOSSIER_REPORT_TYPE,
        file_path=str(tmp_path / "unlinked.docx"),
        generated_at=datetime.now(timezone.utc),
        template_version="1.0",
    )
    missing_risk_report = GeneratedReport(
        report_type=RISK_DOSSIER_REPORT_TYPE,
        risk_record_id=uuid.uuid4(),
        file_path=str(tmp_path / "missing-risk.docx"),
        generated_at=datetime.now(timezone.utc),
        template_version="1.0",
    )
    db_session.add_all([unlinked_report, missing_risk_report])
    db_session.flush()

    with pytest.raises(ReportTrackingBusinessRuleError, match="not linked"):
        get_authorized_generated_report_file_path(
            db_session,
            generated_report_id=unlinked_report.id,
            requested_by_user_id=creator.id,
        )
    with pytest.raises(ReportTrackingBusinessRuleError, match="Linked risk record"):
        get_authorized_generated_report_file_path(
            db_session,
            generated_report_id=missing_risk_report.id,
            requested_by_user_id=creator.id,
        )
    with pytest.raises(GeneratedReportNotFoundError):
        get_authorized_generated_report_file_path(
            db_session,
            generated_report_id=uuid.uuid4(),
            requested_by_user_id=creator.id,
        )


def test_get_generated_report_file_path_raises_for_unknown_report(
    db_session: Session,
) -> None:
    with pytest.raises(GeneratedReportNotFoundError):
        get_generated_report_file_path(db_session, generated_report_id=uuid.uuid4())


@pytest.mark.parametrize("file_path", ["missing.docx", ""])
def test_get_generated_report_file_path_raises_for_missing_file(
    db_session: Session,
    tmp_path: Path,
    file_path: str,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)
    generated_report.file_path = str(tmp_path / file_path) if file_path else file_path

    with pytest.raises(ReportTrackingBusinessRuleError):
        get_generated_report_file_path(
            db_session,
            generated_report_id=generated_report.id,
        )


def test_get_generated_report_file_path_raises_for_directory(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)
    generated_report.file_path = str(tmp_path)

    with pytest.raises(ReportTrackingBusinessRuleError):
        get_generated_report_file_path(
            db_session,
            generated_report_id=generated_report.id,
        )


def test_list_generated_reports_returns_reports(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    assert generated_report in list_generated_reports(db_session)


def test_list_generated_reports_filters_by_risk_record_id(
    db_session: Session,
    tmp_path: Path,
) -> None:
    first_risk = _create_risk_record(db_session, risk_id="RISK-2026-0001")
    second_risk = _create_risk_record(db_session, risk_id="RISK-2026-0002")
    first_report = _generate_report(db_session, tmp_path, risk_record=first_risk)
    second_report = _generate_report(db_session, tmp_path, risk_record=second_risk)

    reports = list_generated_reports(db_session, risk_record_id=first_risk.id)

    assert first_report in reports
    assert second_report not in reports


def test_list_generated_reports_filters_by_report_type(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    reports = list_generated_reports(db_session, report_type=RISK_DOSSIER_REPORT_TYPE)

    assert reports == [generated_report]


def test_authorized_report_list_and_get_follow_linked_risk_scope(
    db_session: Session,
    tmp_path: Path,
) -> None:
    first_creator = _create_user(db_session)
    second_creator = _create_user(db_session)
    first_board = _create_committee(db_session)
    second_board = _create_committee(db_session)
    first_member = _create_user(db_session)
    _create_membership(db_session, committee=first_board, user=first_member)
    first_risk = _create_risk_record(
        db_session,
        risk_id="RISK-2026-2001",
        creator=first_creator,
        board_of_origin_id=first_board.id,
    )
    second_risk = _create_risk_record(
        db_session,
        risk_id="RISK-2026-2002",
        creator=second_creator,
        board_of_origin_id=second_board.id,
    )
    first_report = _generate_report(db_session, tmp_path, risk_record=first_risk)
    second_report = _generate_report(db_session, tmp_path, risk_record=second_risk)

    assert list_authorized_generated_reports(
        db_session, requested_by_user_id=first_member.id
    ) == [first_report]
    assert get_authorized_generated_report(
        db_session,
        generated_report_id=first_report.id,
        requested_by_user_id=first_member.id,
    ) is first_report
    with pytest.raises(ReportTrackingBusinessRuleError, match="not authorized"):
        get_authorized_generated_report(
            db_session,
            generated_report_id=second_report.id,
            requested_by_user_id=first_member.id,
        )


def test_authorized_report_list_and_get_require_active_user(
    db_session: Session,
    tmp_path: Path,
) -> None:
    report = _generate_report(db_session, tmp_path)

    with pytest.raises(ReportTrackingBusinessRuleError, match="authenticated active user"):
        list_authorized_generated_reports(db_session, requested_by_user_id=None)
    with pytest.raises(ReportTrackingBusinessRuleError, match="authenticated active user"):
        get_authorized_generated_report(
            db_session,
            generated_report_id=report.id,
            requested_by_user_id=None,
        )
