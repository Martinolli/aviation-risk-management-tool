import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel
from app.models.report import GeneratedReport
from app.models.risk import RiskRecord
from app.models.user import User
from app.services.report_service import (
    ReportRiskNotFoundError,
    generate_risk_dossier_docx,
)

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
    if user_id is None:
        if operation == "download":
            raise ReportTrackingBusinessRuleError(
                "Report download requires an authenticated active user"
            )
        raise ReportTrackingBusinessRuleError(
            "Report generation requires an authenticated active user"
        )

    user = db.get(User, user_id)
    if user is None:
        if operation == "download":
            raise ReportTrackingBusinessRuleError("Report download user does not exist")
        raise ReportTrackingBusinessRuleError("Report generation user does not exist")
    if not user.is_active:
        if operation == "download":
            raise ReportTrackingBusinessRuleError("Report download user is inactive")
        raise ReportTrackingBusinessRuleError("Report generation user is inactive")
    return user


def _validate_report_risk_access_authority(
    db: Session,
    *,
    risk_record: RiskRecord,
    actor_user_id: uuid.UUID,
    operation: str,
) -> None:
    if actor_user_id in {risk_record.owner_user_id, risk_record.created_by_user_id}:
        return

    if risk_record.board_of_origin_id is not None:
        board_membership = db.scalar(
            select(CommitteeMember.id)
            .join(Committee, CommitteeMember.committee_id == Committee.id)
            .where(
                CommitteeMember.committee_id == risk_record.board_of_origin_id,
                CommitteeMember.user_id == actor_user_id,
                CommitteeMember.is_active.is_(True),
                Committee.is_active.is_(True),
            )
        )
        if board_membership is not None:
            return

    governance_membership = db.scalar(
        select(CommitteeMember.id)
        .join(Committee, CommitteeMember.committee_id == Committee.id)
        .where(
            CommitteeMember.user_id == actor_user_id,
            CommitteeMember.is_active.is_(True),
            Committee.is_active.is_(True),
            Committee.is_fixed.is_(True),
            Committee.authority_level.in_([AuthorityLevel.MIDDLE, AuthorityLevel.HIGH]),
        )
    )
    if governance_membership is not None:
        return

    if operation == "download":
        raise ReportTrackingBusinessRuleError(
            "User is not authorized to download this risk report"
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
