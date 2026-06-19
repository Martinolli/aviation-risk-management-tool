import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.models.report import GeneratedReport
from app.models.risk import RiskRecord
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
