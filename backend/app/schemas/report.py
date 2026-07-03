import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class GeneratedReportRead(BaseModel):
    id: uuid.UUID
    risk_record_id: uuid.UUID | None
    committee_id: uuid.UUID | None
    report_type: str
    file_path: str
    generated_by_user_id: uuid.UUID | None
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenerateRiskDossierReportRequest(BaseModel):
    output_dir: str | None = None

    model_config = ConfigDict(extra="forbid")


class GenerateRiskEvidencePackageRequest(BaseModel):
    output_dir: str | None = None
    include_archived: bool = False
    include_risk_dossier: bool = True

    model_config = ConfigDict(extra="forbid")


class GenerateCommitteeMeetingPackRequest(BaseModel):
    output_dir: str | None = None
    meeting_title: str | None = None
    meeting_date: date | None = None

    model_config = ConfigDict(extra="forbid")
