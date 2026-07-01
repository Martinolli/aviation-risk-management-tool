import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.audit_service as audit_service
from app.core.config import settings
from app.models.risk import RiskEvidence, RiskRecord
from app.models.user import User
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    validate_active_user,
)

RISK_EVIDENCE_ENTITY_TYPE = "RiskEvidence"
COPY_CHUNK_SIZE = 1024 * 1024
DANGEROUS_CONTENT_TYPES = {
    "application/x-bat",
    "application/x-cmd",
    "application/x-msdos-program",
    "application/x-msdownload",
    "application/x-sh",
}


class RiskEvidenceNotFoundError(ValueError):
    pass


class RiskEvidenceBusinessRuleError(ValueError):
    pass


def _validate_actor(
    db: Session,
    *,
    user_id: uuid.UUID | None,
    context: str,
) -> User:
    try:
        return validate_active_user(db, user_id=user_id, context=context)
    except RiskAccessBusinessRuleError as exc:
        raise RiskEvidenceBusinessRuleError(str(exc)) from exc


def _get_risk_record(db: Session, *, risk_record_id: uuid.UUID) -> RiskRecord:
    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise RiskEvidenceNotFoundError("Risk record not found")
    return risk_record


def _authorize_risk_access(
    db: Session,
    *,
    risk_record: RiskRecord,
    user_id: uuid.UUID,
    operation: str,
) -> None:
    if not can_read_risk_record(db, risk_record=risk_record, user_id=user_id):
        raise RiskEvidenceBusinessRuleError(
            f"User is not authorized to {operation} evidence for this risk"
        )


def _display_filename(filename: str) -> str:
    # Browsers normally send a base filename. Normalizing both separator styles
    # also protects direct API clients from persisting traversal components.
    return filename.replace("\\", "/").rsplit("/", 1)[-1].strip()


def _safe_filename(filename: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    if not sanitized:
        sanitized = "evidence"
    return sanitized[:180]


def validate_evidence_file(upload_file: UploadFile) -> str:
    if not upload_file.filename or not upload_file.filename.strip():
        raise RiskEvidenceBusinessRuleError("Evidence file must have a filename")

    original_filename = _display_filename(upload_file.filename)
    if not original_filename or original_filename in {".", ".."}:
        raise RiskEvidenceBusinessRuleError("Evidence file must have a valid filename")

    content_type = (upload_file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type in DANGEROUS_CONTENT_TYPES:
        raise RiskEvidenceBusinessRuleError(
            "This evidence file type is not allowed"
        )

    declared_size = upload_file.size
    if declared_size is not None:
        if declared_size <= 0:
            raise RiskEvidenceBusinessRuleError("Evidence file must not be empty")
        if declared_size > settings.max_evidence_upload_bytes:
            raise RiskEvidenceBusinessRuleError(
                f"Evidence file exceeds the {settings.max_evidence_upload_mb} MB limit"
            )

    return original_filename


def get_evidence_storage_directory() -> Path:
    storage_directory = Path(settings.evidence_storage_dir).expanduser()
    if not storage_directory.is_absolute():
        repository_root = Path(__file__).resolve().parents[3]
        storage_directory = repository_root / storage_directory
    storage_directory.mkdir(parents=True, exist_ok=True)
    return storage_directory.resolve()


def upload_risk_evidence(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    upload_file: UploadFile,
    description: str | None,
    uploaded_by_user_id: uuid.UUID | None,
) -> RiskEvidence:
    uploader = _validate_actor(
        db,
        user_id=uploaded_by_user_id,
        context="Evidence upload",
    )
    risk_record = _get_risk_record(db, risk_record_id=risk_record_id)
    _authorize_risk_access(
        db,
        risk_record=risk_record,
        user_id=uploader.id,
        operation="upload",
    )
    if not risk_record.is_active:
        raise RiskEvidenceBusinessRuleError(
            "Evidence cannot be uploaded to an inactive risk record"
        )

    original_filename = validate_evidence_file(upload_file)
    stored_filename = f"{uuid.uuid4()}_{_safe_filename(original_filename)}"
    risk_directory = get_evidence_storage_directory() / str(risk_record.id)
    risk_directory.mkdir(parents=True, exist_ok=True)
    storage_path = risk_directory / stored_filename
    file_size_bytes = 0

    try:
        upload_file.file.seek(0)
        with storage_path.open("xb") as stored_file:
            while chunk := upload_file.file.read(COPY_CHUNK_SIZE):
                file_size_bytes += len(chunk)
                if file_size_bytes > settings.max_evidence_upload_bytes:
                    raise RiskEvidenceBusinessRuleError(
                        f"Evidence file exceeds the {settings.max_evidence_upload_mb} MB limit"
                    )
                stored_file.write(chunk)
        if file_size_bytes == 0:
            raise RiskEvidenceBusinessRuleError("Evidence file must not be empty")
    except RiskEvidenceBusinessRuleError:
        storage_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        storage_path.unlink(missing_ok=True)
        raise RiskEvidenceBusinessRuleError(
            "Unable to store the evidence file"
        ) from exc

    evidence = RiskEvidence(
        risk_record_id=risk_record.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_path=str(storage_path),
        content_type=upload_file.content_type,
        file_size_bytes=file_size_bytes,
        description=description.strip() if description and description.strip() else None,
        uploaded_by_user_id=uploader.id,
        uploaded_at=datetime.now(timezone.utc),
        is_active=True,
    )

    try:
        db.add(evidence)
        db.flush()
        audit_service.log_entity_created(
            db,
            entity_type=RISK_EVIDENCE_ENTITY_TYPE,
            entity_id=evidence.id,
            created_by_user_id=uploader.id,
            new_value={
                "risk_record_id": risk_record.id,
                "original_filename": evidence.original_filename,
                "file_size_bytes": evidence.file_size_bytes,
            },
        )
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise

    return evidence


def list_risk_evidence(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
    include_archived: bool = False,
) -> list[RiskEvidence]:
    reader = _validate_actor(
        db,
        user_id=requested_by_user_id,
        context="Evidence list access",
    )
    risk_record = _get_risk_record(db, risk_record_id=risk_record_id)
    _authorize_risk_access(
        db,
        risk_record=risk_record,
        user_id=reader.id,
        operation="list",
    )

    statement = select(RiskEvidence).where(
        RiskEvidence.risk_record_id == risk_record.id
    )
    if not include_archived:
        statement = statement.where(RiskEvidence.is_active.is_(True))
    statement = statement.order_by(
        RiskEvidence.uploaded_at.desc(), RiskEvidence.created_at.desc()
    )
    return list(db.scalars(statement).all())


def get_risk_evidence(
    db: Session,
    *,
    evidence_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> RiskEvidence:
    reader = _validate_actor(
        db,
        user_id=requested_by_user_id,
        context="Evidence access",
    )
    evidence = db.get(RiskEvidence, evidence_id)
    if evidence is None:
        raise RiskEvidenceNotFoundError("Evidence not found")
    risk_record = _get_risk_record(db, risk_record_id=evidence.risk_record_id)
    _authorize_risk_access(
        db,
        risk_record=risk_record,
        user_id=reader.id,
        operation="read",
    )
    return evidence


def get_risk_evidence_file_path(
    db: Session,
    *,
    evidence_id: uuid.UUID,
    requested_by_user_id: uuid.UUID | None,
) -> tuple[RiskEvidence, Path]:
    evidence = get_risk_evidence(
        db,
        evidence_id=evidence_id,
        requested_by_user_id=requested_by_user_id,
    )
    storage_root = get_evidence_storage_directory()
    try:
        file_path = Path(evidence.storage_path).resolve()
        file_path.relative_to(storage_root)
    except (OSError, ValueError) as exc:
        raise RiskEvidenceBusinessRuleError(
            "Evidence file path is invalid"
        ) from exc
    if not file_path.is_file():
        raise RiskEvidenceBusinessRuleError("Evidence file does not exist")
    return evidence, file_path


def archive_risk_evidence(
    db: Session,
    *,
    evidence_id: uuid.UUID,
    archived_by_user_id: uuid.UUID | None,
    archive_reason: str | None,
) -> RiskEvidence:
    archiver = _validate_actor(
        db,
        user_id=archived_by_user_id,
        context="Evidence archive",
    )
    evidence = db.get(RiskEvidence, evidence_id)
    if evidence is None:
        raise RiskEvidenceNotFoundError("Evidence not found")
    risk_record = _get_risk_record(db, risk_record_id=evidence.risk_record_id)
    _authorize_risk_access(
        db,
        risk_record=risk_record,
        user_id=archiver.id,
        operation="archive",
    )
    if not evidence.is_active:
        raise RiskEvidenceBusinessRuleError("Evidence is already archived")

    archived_at = datetime.now(timezone.utc)
    normalized_reason = (
        archive_reason.strip() if archive_reason and archive_reason.strip() else None
    )
    old_value = {"is_active": True, "archived_at": None}
    evidence.is_active = False
    evidence.archived_at = archived_at
    evidence.archived_by_user_id = archiver.id
    evidence.archive_reason = normalized_reason
    db.flush()

    audit_service.log_archive_action(
        db,
        entity_type=RISK_EVIDENCE_ENTITY_TYPE,
        entity_id=evidence.id,
        changed_by_user_id=archiver.id,
        old_value=old_value,
        new_value={
            "risk_record_id": evidence.risk_record_id,
            "original_filename": evidence.original_filename,
            "is_active": False,
            "archived_at": archived_at,
            "archive_reason": normalized_reason,
        },
        reason=normalized_reason,
    )
    return evidence
