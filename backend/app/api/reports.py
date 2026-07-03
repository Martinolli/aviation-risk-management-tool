import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_optional_current_user, get_optional_current_user_id
from app.core.database import get_db
from app.models.report import GeneratedReport
from app.models.user import User
from app.schemas.report import (
    GenerateCommitteeMeetingPackRequest,
    GenerateRiskDossierReportRequest,
    GenerateRiskEvidencePackageRequest,
    GeneratedReportRead,
)
from app.services.report_tracking_service import (
    GeneratedReportNotFoundError,
    ReportTrackingBusinessRuleError,
    generate_and_track_committee_meeting_pack,
    generate_and_track_risk_dossier_report,
    generate_and_track_risk_evidence_package,
    get_authorized_generated_report_file_path,
    get_authorized_generated_report,
    list_authorized_generated_reports,
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _media_type_for_report(file_path: Path, report_type: str) -> str:
    if report_type.endswith("_ZIP") or file_path.suffix.lower() == ".zip":
        return "application/zip"
    return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


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


@router.post(
    "/risk-evidence-packages/{risk_record_id}",
    response_model=GeneratedReportRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_risk_evidence_package_endpoint(
    risk_record_id: uuid.UUID,
    data: GenerateRiskEvidencePackageRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        generated_report = generate_and_track_risk_evidence_package(
            db,
            risk_record_id=risk_record_id,
            output_dir=data.output_dir if data is not None else None,
            generated_by_user_id=get_optional_current_user_id(current_user),
            include_archived=data.include_archived if data is not None else False,
            include_risk_dossier=(
                data.include_risk_dossier if data is not None else True
            ),
        )
        return _commit_and_refresh(db, generated_report)
    except ReportTrackingBusinessRuleError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/committee-meeting-packs/{committee_id}",
    response_model=GeneratedReportRead,
    status_code=status.HTTP_201_CREATED,
)
def generate_committee_meeting_pack_endpoint(
    committee_id: uuid.UUID,
    data: GenerateCommitteeMeetingPackRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        generated_report = generate_and_track_committee_meeting_pack(
            db,
            committee_id=committee_id,
            output_dir=data.output_dir if data is not None else None,
            generated_by_user_id=get_optional_current_user_id(current_user),
            meeting_title=data.meeting_title if data is not None else None,
            meeting_date=data.meeting_date if data is not None else None,
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
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        return list_authorized_generated_reports(
            db,
            requested_by_user_id=get_optional_current_user_id(current_user),
            risk_record_id=risk_record_id,
            report_type=report_type,
        )
    except ReportTrackingBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{generated_report_id}/download")
def download_generated_report_endpoint(
    generated_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        file_path = get_authorized_generated_report_file_path(
            db,
            generated_report_id=generated_report_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
        )
        generated_report = db.get(GeneratedReport, generated_report_id)
        if generated_report is None:
            raise GeneratedReportNotFoundError("Generated report not found")
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
        media_type=_media_type_for_report(
            file_path,
            generated_report.report_type,
        ),
        filename=file_path.name,
    )


@router.get("/{generated_report_id}", response_model=GeneratedReportRead)
def get_generated_report_endpoint(
    generated_report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        generated_report = get_authorized_generated_report(
            db,
            generated_report_id=generated_report_id,
            requested_by_user_id=get_optional_current_user_id(current_user),
        )
        if generated_report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generated report not found",
            )
        return generated_report
    except ReportTrackingBusinessRuleError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
