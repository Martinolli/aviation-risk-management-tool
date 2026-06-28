import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.report import GeneratedReport
from app.models.risk import RiskRecord
from app.models.user import User
from app.services.report_service import (
    ReportRiskNotFoundError,
    generate_risk_dossier_docx,
)
from app.services.risk_access_service import can_read_risk_record, validate_active_user

DEFAULT_REPORT_OUTPUT_DIR = Path("generated_reports")
RISK_DOSSIER_REPORT_TYPE = "RISK_DOSSIER_DOCX"
RISK_DOSSIER_TEMPLATE_VERSION = "1.0"


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
    _validate_report_actor(db, user_id=requested_by_user_id, operation="get")
    generated_report = db.get(GeneratedReport, generated_report_id)
    if generated_report is None:
        return None
    if generated_report.risk_record_id is None:
        raise ReportTrackingBusinessRuleError(
            "Generated report is not linked to a risk record"
        )
    risk_record = db.get(RiskRecord, generated_report.risk_record_id)
    if risk_record is None:
        raise ReportTrackingBusinessRuleError("Linked risk record does not exist")
    _validate_report_risk_access_authority(
        db,
        risk_record=risk_record,
        actor_user_id=requested_by_user_id,
        operation="get",
    )
    return generated_report


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
    _validate_report_actor(
        db,
        user_id=requested_by_user_id,
        operation="download",
    )

    generated_report = db.get(GeneratedReport, generated_report_id)
    if generated_report is None:
        raise GeneratedReportNotFoundError("Generated report not found")
    if generated_report.risk_record_id is None:
        raise ReportTrackingBusinessRuleError(
            "Generated report is not linked to a risk record"
        )

    risk_record = db.get(RiskRecord, generated_report.risk_record_id)
    if risk_record is None:
        raise ReportTrackingBusinessRuleError("Linked risk record does not exist")
    _validate_report_risk_access_authority(
        db,
        risk_record=risk_record,
        actor_user_id=requested_by_user_id,
        operation="download",
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
    _validate_report_actor(db, user_id=requested_by_user_id, operation="list")
    reports = list_generated_reports(
        db,
        risk_record_id=risk_record_id,
        report_type=report_type,
    )
    authorized_reports: list[GeneratedReport] = []
    for report in reports:
        if report.risk_record_id is None:
            continue
        risk_record = db.get(RiskRecord, report.risk_record_id)
        if risk_record is not None and can_read_risk_record(
            db,
            risk_record=risk_record,
            user_id=requested_by_user_id,
        ):
            authorized_reports.append(report)
    return authorized_reports
