import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee
from app.models.committee_meeting import CommitteeMeeting
from app.models.report import GeneratedReport
from app.models.risk import RiskRecord
from app.models.user import User
from app.services.report_service import (
    ReportRiskNotFoundError,
    generate_risk_dossier_docx,
)
from app.services.risk_evidence_package_service import (
    RiskEvidencePackageBusinessRuleError,
    generate_risk_evidence_package_zip,
)
from app.services.committee_meeting_pack_service import (
    CommitteeMeetingPackBusinessRuleError,
    generate_committee_meeting_pack_docx,
)
from app.services.committee_meeting_minutes_report_service import (
    CommitteeMeetingMinutesReportBusinessRuleError,
    generate_committee_meeting_minutes_docx,
)
from app.services.risk_access_service import (
    can_read_risk_record,
    is_active_committee_member,
    validate_active_user,
)

DEFAULT_REPORT_OUTPUT_DIR = Path("generated_reports")
RISK_DOSSIER_REPORT_TYPE = "RISK_DOSSIER_DOCX"
RISK_DOSSIER_TEMPLATE_VERSION = "1.0"
COMMITTEE_MEETING_PACK_REPORT_TYPE = "COMMITTEE_MEETING_PACK_DOCX"
COMMITTEE_MEETING_PACK_TEMPLATE_VERSION = "1.0"
COMMITTEE_MEETING_MINUTES_REPORT_TYPE = "COMMITTEE_MEETING_MINUTES_DOCX"
COMMITTEE_MEETING_MINUTES_TEMPLATE_VERSION = "1.0"
RISK_EVIDENCE_PACKAGE_REPORT_TYPE = "RISK_EVIDENCE_PACKAGE_ZIP"
RISK_EVIDENCE_PACKAGE_TEMPLATE_VERSION = "1.0"


class GeneratedReportNotFoundError(ValueError):
    pass


class ReportTrackingBusinessRuleError(ValueError):
    pass


def _validate_report_actor(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    operation: str,
) -> User:
    context = {
        "generation": "Report generation",
        "download": "Report download",
        "list": "Report list access",
        "get": "Report detail access",
    }[operation]
    try:
        return validate_active_user(db, user_id=user_id, context=context)
    except ValueError as exc:
        raise ReportTrackingBusinessRuleError(str(exc)) from exc


def _validate_report_risk_access_authority(
    db: Session,
    *,
    risk_record: RiskRecord,
    actor_user_id: uuid.UUID,
    operation: str,
) -> None:
    if can_read_risk_record(db, risk_record=risk_record, user_id=actor_user_id):
        return

    if operation == "download":
        raise ReportTrackingBusinessRuleError(
            "User is not authorized to download this risk report"
        )
    if operation == "get":
        raise ReportTrackingBusinessRuleError(
            "User is not authorized to read this generated report"
        )
    raise ReportTrackingBusinessRuleError("User is not authorized to generate this risk report")


def _validate_report_committee_access_authority(
    db: Session,
    *,
    committee: Committee,
    actor_user_id: uuid.UUID,
    operation: str,
) -> None:
    if not committee.is_active:
        raise ReportTrackingBusinessRuleError("Committee is inactive")
    if is_active_committee_member(
        db,
        committee_id=committee.id,
        user_id=actor_user_id,
    ):
        return

    if operation == "download":
        raise ReportTrackingBusinessRuleError(
            "User is not authorized to download this committee report"
        )
    if operation == "get":
        raise ReportTrackingBusinessRuleError(
            "User is not authorized to read this generated report"
        )
    raise ReportTrackingBusinessRuleError(
        "User is not authorized to generate a meeting pack for this committee"
    )


def generate_and_track_risk_dossier_report(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    output_dir: Path | str | None = None,
    generated_by_user_id: uuid.UUID | None = None,
) -> GeneratedReport:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise ReportTrackingBusinessRuleError("Risk record does not exist")
    _validate_report_actor(
        db,
        user_id=generated_by_user_id,
        operation="generation",
    )
    _validate_report_risk_access_authority(
        db,
        risk_record=risk_record,
        actor_user_id=generated_by_user_id,
        operation="generation",
    )

    try:
        file_path = generate_risk_dossier_docx(
            db,
            risk_record_id=risk_record_id,
            output_dir=output_dir or DEFAULT_REPORT_OUTPUT_DIR,
        )
    except ReportRiskNotFoundError as exc:
        raise ReportTrackingBusinessRuleError("Risk record does not exist") from exc

    generated_report = GeneratedReport(
        risk_record_id=risk_record.id,
        report_type=RISK_DOSSIER_REPORT_TYPE,
        file_path=str(file_path),
        generated_by_user_id=generated_by_user_id,
        generated_at=datetime.now(timezone.utc),
        template_version=RISK_DOSSIER_TEMPLATE_VERSION,
    )
    db.add(generated_report)
    db.flush()

    audit_service.log_report_generated(
        db,
        entity_type="RiskRecord",
        entity_id=risk_record.id,
        generated_by_user_id=generated_by_user_id,
        report_metadata={
            "report_id": generated_report.id,
            "report_type": generated_report.report_type,
            "file_path": generated_report.file_path,
            "template_version": generated_report.template_version,
        },
    )
    return generated_report


def generate_and_track_risk_evidence_package(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    output_dir: Path | str | None = None,
    generated_by_user_id: uuid.UUID | None,
    include_archived: bool = False,
    include_risk_dossier: bool = True,
) -> GeneratedReport:
    actor = _validate_report_actor(
        db,
        user_id=generated_by_user_id,
        operation="generation",
    )
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise ReportTrackingBusinessRuleError("Risk record does not exist")
    _validate_report_risk_access_authority(
        db,
        risk_record=risk_record,
        actor_user_id=actor.id,
        operation="generation",
    )
    if not risk_record.is_active:
        raise ReportTrackingBusinessRuleError(
            "Risk Evidence Package cannot be generated for an inactive risk record"
        )

    try:
        file_path = generate_risk_evidence_package_zip(
            db,
            risk_record_id=risk_record.id,
            generated_by_user_id=actor.id,
            output_dir=output_dir or DEFAULT_REPORT_OUTPUT_DIR,
            include_archived=include_archived,
            include_risk_dossier=include_risk_dossier,
        )
    except RiskEvidencePackageBusinessRuleError as exc:
        raise ReportTrackingBusinessRuleError(str(exc)) from exc

    generated_report = GeneratedReport(
        risk_record_id=risk_record.id,
        committee_id=None,
        report_type=RISK_EVIDENCE_PACKAGE_REPORT_TYPE,
        file_path=str(file_path),
        generated_by_user_id=actor.id,
        generated_at=datetime.now(timezone.utc),
        template_version=RISK_EVIDENCE_PACKAGE_TEMPLATE_VERSION,
    )
    db.add(generated_report)
    db.flush()

    audit_service.log_report_generated(
        db,
        entity_type="RiskRecord",
        entity_id=risk_record.id,
        generated_by_user_id=actor.id,
        report_metadata={
            "report_id": generated_report.id,
            "report_type": generated_report.report_type,
            "file_path": generated_report.file_path,
            "template_version": generated_report.template_version,
            "include_archived": include_archived,
            "include_risk_dossier": include_risk_dossier,
        },
    )
    return generated_report


def generate_and_track_committee_meeting_pack(
    db: Session,
    *,
    committee_id: uuid.UUID,
    output_dir: Path | str | None = None,
    generated_by_user_id: uuid.UUID | None,
    meeting_title: str | None = None,
    meeting_date: date | None = None,
) -> GeneratedReport:
    actor = _validate_report_actor(
        db,
        user_id=generated_by_user_id,
        operation="generation",
    )
    committee = db.get(Committee, committee_id)
    if committee is None:
        raise ReportTrackingBusinessRuleError("Committee does not exist")
    _validate_report_committee_access_authority(
        db,
        committee=committee,
        actor_user_id=actor.id,
        operation="generation",
    )

    try:
        file_path = generate_committee_meeting_pack_docx(
            db,
            committee_id=committee.id,
            generated_by_user_id=actor.id,
            output_dir=output_dir or DEFAULT_REPORT_OUTPUT_DIR,
            meeting_title=meeting_title,
            meeting_date=meeting_date,
        )
    except CommitteeMeetingPackBusinessRuleError as exc:
        raise ReportTrackingBusinessRuleError(str(exc)) from exc

    generated_report = GeneratedReport(
        committee_id=committee.id,
        risk_record_id=None,
        report_type=COMMITTEE_MEETING_PACK_REPORT_TYPE,
        file_path=str(file_path),
        generated_by_user_id=actor.id,
        generated_at=datetime.now(timezone.utc),
        template_version=COMMITTEE_MEETING_PACK_TEMPLATE_VERSION,
    )
    db.add(generated_report)
    db.flush()

    audit_service.log_report_generated(
        db,
        entity_type="Committee",
        entity_id=committee.id,
        generated_by_user_id=actor.id,
        report_metadata={
            "report_id": generated_report.id,
            "report_type": generated_report.report_type,
            "file_path": generated_report.file_path,
            "template_version": generated_report.template_version,
            "meeting_date": meeting_date.isoformat() if meeting_date else None,
        },
    )
    return generated_report


def generate_and_track_committee_meeting_minutes_report(
    db: Session,
    *,
    meeting_id: uuid.UUID,
    output_dir: Path | str | None = None,
    generated_by_user_id: uuid.UUID | None,
) -> GeneratedReport:
    actor = _validate_report_actor(
        db,
        user_id=generated_by_user_id,
        operation="generation",
    )
    meeting = db.get(CommitteeMeeting, meeting_id)
    if meeting is None:
        raise ReportTrackingBusinessRuleError("Committee Meeting Minutes not found")
    committee = db.get(Committee, meeting.committee_id)
    if committee is None:
        raise ReportTrackingBusinessRuleError("Committee does not exist")
    _validate_report_committee_access_authority(
        db,
        committee=committee,
        actor_user_id=actor.id,
        operation="generation",
    )

    try:
        file_path = generate_committee_meeting_minutes_docx(
            db,
            meeting_id=meeting.id,
            generated_by_user_id=actor.id,
            output_dir=output_dir or DEFAULT_REPORT_OUTPUT_DIR,
        )
    except CommitteeMeetingMinutesReportBusinessRuleError as exc:
        raise ReportTrackingBusinessRuleError(str(exc)) from exc

    generated_report = GeneratedReport(
        committee_id=meeting.committee_id,
        risk_record_id=None,
        report_type=COMMITTEE_MEETING_MINUTES_REPORT_TYPE,
        file_path=str(file_path),
        generated_by_user_id=actor.id,
        generated_at=datetime.now(timezone.utc),
        template_version=COMMITTEE_MEETING_MINUTES_TEMPLATE_VERSION,
    )
    db.add(generated_report)
    db.flush()

    audit_service.log_report_generated(
        db,
        entity_type="CommitteeMeeting",
        entity_id=meeting.id,
        generated_by_user_id=actor.id,
        report_metadata={
            "meeting_id": meeting.id,
            "committee_id": meeting.committee_id,
            "report_id": generated_report.id,
            "report_type": generated_report.report_type,
            "file_path": generated_report.file_path,
            "template_version": generated_report.template_version,
        },
    )
    return generated_report


def get_generated_report(
    db: Session,
    *,
    generated_report_id: uuid.UUID,
) -> GeneratedReport | None:
    return db.get(GeneratedReport, generated_report_id)


def get_authorized_generated_report(
    db: Session,
    *,
    generated_report_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> GeneratedReport | None:
    actor = _validate_report_actor(
        db, user_id=requested_by_user_id, operation="get"
    )
    generated_report = db.get(GeneratedReport, generated_report_id)
    if generated_report is None:
        return None
    if generated_report.risk_record_id is not None:
        risk_record = db.get(RiskRecord, generated_report.risk_record_id)
        if risk_record is None:
            raise ReportTrackingBusinessRuleError("Linked risk record does not exist")
        _validate_report_risk_access_authority(
            db,
            risk_record=risk_record,
            actor_user_id=actor.id,
            operation="get",
        )
        return generated_report
    if generated_report.committee_id is not None:
        committee = db.get(Committee, generated_report.committee_id)
        if committee is None:
            raise ReportTrackingBusinessRuleError("Linked committee does not exist")
        _validate_report_committee_access_authority(
            db,
            committee=committee,
            actor_user_id=actor.id,
            operation="get",
        )
        return generated_report
    raise ReportTrackingBusinessRuleError(
        "Generated report is not linked to a risk record or committee"
    )


def get_generated_report_file_path(
    db: Session,
    *,
    generated_report_id: uuid.UUID,
) -> Path:
    generated_report = db.get(GeneratedReport, generated_report_id)
    if generated_report is None:
        raise GeneratedReportNotFoundError("Generated report not found")

    if not generated_report.file_path:
        raise ReportTrackingBusinessRuleError("Generated report file path is missing")

    try:
        file_path = Path(generated_report.file_path)
        file_exists = file_path.exists()
        is_file = file_path.is_file()
    except (OSError, ValueError, TypeError) as exc:
        raise ReportTrackingBusinessRuleError("Generated report file path is invalid") from exc

    if not file_exists:
        raise ReportTrackingBusinessRuleError("Generated report file does not exist")
    if not is_file:
        raise ReportTrackingBusinessRuleError("Generated report path is not a file")

    return file_path


def get_authorized_generated_report_file_path(
    db: Session,
    *,
    generated_report_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> Path:
    actor = _validate_report_actor(
        db,
        user_id=requested_by_user_id,
        operation="download",
    )

    generated_report = db.get(GeneratedReport, generated_report_id)
    if generated_report is None:
        raise GeneratedReportNotFoundError("Generated report not found")
    if generated_report.risk_record_id is not None:
        risk_record = db.get(RiskRecord, generated_report.risk_record_id)
        if risk_record is None:
            raise ReportTrackingBusinessRuleError("Linked risk record does not exist")
        _validate_report_risk_access_authority(
            db,
            risk_record=risk_record,
            actor_user_id=actor.id,
            operation="download",
        )
    elif generated_report.committee_id is not None:
        committee = db.get(Committee, generated_report.committee_id)
        if committee is None:
            raise ReportTrackingBusinessRuleError("Linked committee does not exist")
        _validate_report_committee_access_authority(
            db,
            committee=committee,
            actor_user_id=actor.id,
            operation="download",
        )
    else:
        raise ReportTrackingBusinessRuleError(
            "Generated report is not linked to a risk record or committee"
        )
    return get_generated_report_file_path(
        db,
        generated_report_id=generated_report_id,
    )


def list_generated_reports(
    db: Session,
    *,
    risk_record_id: uuid.UUID | None = None,
    report_type: str | None = None,
) -> list[GeneratedReport]:
    statement = select(GeneratedReport).order_by(GeneratedReport.generated_at.desc())
    if risk_record_id is not None:
        statement = statement.where(GeneratedReport.risk_record_id == risk_record_id)
    if report_type is not None:
        statement = statement.where(GeneratedReport.report_type == report_type)

    return list(db.scalars(statement).all())


def list_authorized_generated_reports(
    db: Session,
    *,
    requested_by_user_id: uuid.UUID | None,
    risk_record_id: uuid.UUID | None = None,
    report_type: str | None = None,
) -> list[GeneratedReport]:
    actor = _validate_report_actor(
        db, user_id=requested_by_user_id, operation="list"
    )
    reports = list_generated_reports(
        db,
        risk_record_id=risk_record_id,
        report_type=report_type,
    )
    authorized_reports: list[GeneratedReport] = []
    for report in reports:
        if report.risk_record_id is not None:
            risk_record = db.get(RiskRecord, report.risk_record_id)
            if risk_record is not None and can_read_risk_record(
                db,
                risk_record=risk_record,
                user_id=actor.id,
            ):
                authorized_reports.append(report)
        elif report.committee_id is not None:
            committee = db.get(Committee, report.committee_id)
            if (
                committee is not None
                and committee.is_active
                and is_active_committee_member(
                    db,
                    committee_id=committee.id,
                    user_id=actor.id,
                )
            ):
                authorized_reports.append(report)
    return authorized_reports
