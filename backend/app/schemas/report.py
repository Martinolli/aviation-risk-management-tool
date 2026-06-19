import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GeneratedReportRead(BaseModel):
    id: uuid.UUID
    risk_record_id: uuid.UUID | None
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
