import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.report import GeneratedReport
from app.models.user import User
from app.schemas.report import (
    GenerateRiskDossierReportRequest,
    GeneratedReportRead,
)
from app.services.report_tracking_service import (
    GeneratedReportNotFoundError,
    ReportTrackingBusinessRuleError,
    generate_and_track_risk_dossier_report,
    get_generated_report,
    get_generated_report_file_path,
    list_generated_reports,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _commit_and_refresh(
    db: Session,
    generated_report: GeneratedReport,
) -> GeneratedReport:
    db.commit()
    db.refresh(generated_report)
    return generated_report


@router.post(
    "/risk-dossiers/{risk_record_id}",
    response_model=GeneratedReportRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_risk_dossier_report_endpoint(
    risk_record_id: uuid.UUID,
    data: GenerateRiskDossierReportRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        generated_report = generate_and_track_risk_dossier_report(
            db,
            risk_record_id=risk_record_id,
            output_dir=data.output_dir if data is not None else None,
            generated_by_user_id=get_optional_current_user_id(current_user),
        )
        return _commit_and_refresh(db, generated_report)
    except ReportTrackingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("", response_model=list[GeneratedReportRead])
def list_generated_reports_endpoint(
    risk_record_id: uuid.UUID | None = None,
    report_type: str | None = None,
    db: Session = Depends(get_db),
):
    return list_generated_reports(
        db,
        risk_record_id=risk_record_id,
        report_type=report_type,
    )


@router.get("/{generated_report_id}/download")
def download_generated_report_endpoint(
    generated_report_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    try:
        file_path = get_generated_report_file_path(
            db,
            generated_report_id=generated_report_id,
        )
    except GeneratedReportNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ReportTrackingBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=file_path.name,
    )


@router.get("/{generated_report_id}", response_model=GeneratedReportRead)
def get_generated_report_endpoint(
    generated_report_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    generated_report = get_generated_report(
        db,
        generated_report_id=generated_report_id,
    )
    if generated_report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated report not found",
        )
    return generated_report
