import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import (
    AuditAction,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.report import GeneratedReport
from app.models.risk import RiskRecord
from app.services.report_tracking_service import (
    GeneratedReportNotFoundError,
    RISK_DOSSIER_REPORT_TYPE,
    ReportTrackingBusinessRuleError,
    generate_and_track_risk_dossier_report,
    get_generated_report,
    get_generated_report_file_path,
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
) -> RiskRecord:
    risk_record = RiskRecord(
        risk_id=risk_id,
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.flush()
    return risk_record


def _generate_report(
    db_session: Session,
    tmp_path: Path,
    *,
    risk_record: RiskRecord | None = None,
) -> GeneratedReport:
    risk_record = risk_record or _create_risk_record(db_session)
    return generate_and_track_risk_dossier_report(
        db_session,
        risk_record_id=risk_record.id,
        output_dir=tmp_path,
    )


def test_generate_and_track_risk_dossier_report_creates_docx_file(
    db_session: Session,
    tmp_path: Path,
) -> None:
    generated_report = _generate_report(db_session, tmp_path)

    assert Path(generated_report.file_path).exists()
    assert generated_report.file_path.endswith(".docx")


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
