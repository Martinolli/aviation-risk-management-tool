import csv
import hashlib
import io
import json
import re
import tempfile
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk import RiskEvidence, RiskRecord
from app.models.user import User
from app.services.report_service import generate_risk_dossier_docx
from app.services.risk_access_service import (
    RiskAccessBusinessRuleError,
    can_read_risk_record,
    validate_active_user,
)
from app.services.risk_evidence_service import (
    RiskEvidenceBusinessRuleError,
    get_validated_evidence_file_path,
)

MANIFEST_FIELDS = [
    "sequence_number",
    "evidence_id",
    "risk_record_id",
    "risk_id",
    "original_filename",
    "package_filename",
    "content_type",
    "file_size_bytes",
    "sha256",
    "description",
    "uploaded_by_user_id",
    "uploaded_at",
    "is_active",
    "archived_at",
    "archive_reason",
]
README_DISCLAIMER = (
    "This Risk Evidence Package is generated from system records. It supports "
    "review, audit, investigation, and committee preparation. It does not replace "
    "formal committee decision entry, accountable manager acceptance, or required "
    "regulatory documentation."
)
HASH_CHUNK_SIZE = 1024 * 1024


class RiskEvidencePackageBusinessRuleError(ValueError):
    pass


def _validate_request(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    generated_by_user_id: uuid.UUID,
) -> tuple[RiskRecord, User]:
    try:
        user = validate_active_user(
            db,
            user_id=generated_by_user_id,
            context="Risk Evidence Package generation",
        )
    except RiskAccessBusinessRuleError as exc:
        raise RiskEvidencePackageBusinessRuleError(str(exc)) from exc

    risk_record = db.get(RiskRecord, risk_record_id)
    if risk_record is None:
        raise RiskEvidencePackageBusinessRuleError("Risk record does not exist")
    if not can_read_risk_record(
        db,
        risk_record=risk_record,
        user_id=user.id,
    ):
        raise RiskEvidencePackageBusinessRuleError(
            "User is not authorized to generate an Evidence Package for this risk"
        )
    if not risk_record.is_active:
        raise RiskEvidencePackageBusinessRuleError(
            "Risk Evidence Package cannot be generated for an inactive risk record"
        )
    return risk_record, user


def _safe_filename(value: str, *, fallback: str) -> str:
    basename = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", basename).strip("._")
    return (sanitized or fallback)[:180]


def _format_datetime(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        normalized = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return normalized.astimezone(timezone.utc).isoformat()
    return value.isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime | date):
        return _format_datetime(value)
    return value


def _sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as evidence_file:
        while chunk := evidence_file.read(HASH_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_item(
    *,
    sequence_number: int,
    evidence: RiskEvidence,
    risk_record: RiskRecord,
    package_filename: str,
    file_path: Path,
) -> dict[str, Any]:
    return {
        "sequence_number": sequence_number,
        "evidence_id": str(evidence.id),
        "risk_record_id": str(risk_record.id),
        "risk_id": risk_record.risk_id,
        "original_filename": evidence.original_filename,
        "package_filename": package_filename,
        "content_type": evidence.content_type,
        "file_size_bytes": file_path.stat().st_size,
        "sha256": _sha256(file_path),
        "description": evidence.description,
        "uploaded_by_user_id": (
            str(evidence.uploaded_by_user_id)
            if evidence.uploaded_by_user_id is not None
            else None
        ),
        "uploaded_at": _format_datetime(evidence.uploaded_at),
        "is_active": evidence.is_active,
        "archived_at": _format_datetime(evidence.archived_at),
        "archive_reason": evidence.archive_reason,
    }


def _manifest_csv(items: list[dict[str, Any]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=MANIFEST_FIELDS)
    writer.writeheader()
    writer.writerows(items)
    return stream.getvalue()


def _package_readme(
    *,
    risk_record: RiskRecord,
    generated_at: datetime,
    generated_by_user_id: uuid.UUID,
    include_archived: bool,
    include_risk_dossier: bool,
    evidence_count: int,
) -> str:
    contents = [
        "Risk Evidence Package",
        "",
        f"Risk ID: {risk_record.risk_id or 'Not assigned'}",
        f"Risk Record ID: {risk_record.id}",
        f"Generated At UTC: {_format_datetime(generated_at)}",
        f"Generated By User ID: {generated_by_user_id}",
        "",
        "Package Contents",
        "- 01_Risk_Dossier: Fresh Risk Dossier DOCX."
        if include_risk_dossier
        else "- 01_Risk_Dossier: Risk Dossier not requested.",
        f"- 02_Evidence: {evidence_count} packaged Supporting Documents.",
        "- 03_Manifest: Evidence Manifest CSV/JSON and this package readme.",
        f"- Archived evidence included: {'Yes' if include_archived else 'No'}.",
        "",
        "Controlled Export",
        "Evidence files are included without conversion. Manifest SHA256 values "
        "can be used to verify packaged file integrity.",
        "",
        "Disclaimer",
        README_DISCLAIMER,
        "",
    ]
    return "\n".join(contents)


def generate_risk_evidence_package_zip(
    db: Session,
    *,
    risk_record_id: uuid.UUID,
    generated_by_user_id: uuid.UUID,
    output_dir: Path | str,
    include_archived: bool = False,
    include_risk_dossier: bool = True,
) -> Path:
    risk_record, user = _validate_request(
        db,
        risk_record_id=risk_record_id,
        generated_by_user_id=generated_by_user_id,
    )
    statement = (
        select(RiskEvidence)
        .where(RiskEvidence.risk_record_id == risk_record.id)
        .order_by(RiskEvidence.uploaded_at.asc(), RiskEvidence.created_at.asc())
    )
    if not include_archived:
        statement = statement.where(RiskEvidence.is_active.is_(True))

    valid_evidence: list[tuple[RiskEvidence, Path]] = []
    for evidence in db.scalars(statement).all():
        try:
            valid_evidence.append(
                (evidence, get_validated_evidence_file_path(evidence))
            )
        except RiskEvidenceBusinessRuleError:
            continue

    generated_at = datetime.now(timezone.utc)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    risk_name = _safe_filename(
        risk_record.risk_id or str(risk_record.id),
        fallback="risk",
    )
    file_path = output_path / (
        f"{risk_name}_evidence_package_{generated_at.strftime('%Y%m%d_%H%M%S')}.zip"
    )

    manifest_items: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="risk_evidence_package_") as temp_dir:
            dossier_path: Path | None = None
            if include_risk_dossier:
                dossier_path = generate_risk_dossier_docx(
                    db,
                    risk_record_id=risk_record.id,
                    output_dir=temp_dir,
                )

            with ZipFile(file_path, mode="w", compression=ZIP_DEFLATED) as archive:
                archive.writestr("01_Risk_Dossier/", "")
                archive.writestr("02_Evidence/", "")
                archive.writestr("03_Manifest/", "")
                if dossier_path is not None:
                    archive.write(
                        dossier_path,
                        arcname=f"01_Risk_Dossier/{risk_name}_risk_dossier.docx",
                    )

                for sequence_number, (evidence, evidence_path) in enumerate(
                    valid_evidence,
                    start=1,
                ):
                    safe_original = _safe_filename(
                        evidence.original_filename,
                        fallback="evidence",
                    )
                    package_filename = f"{sequence_number:03d}_{safe_original}"
                    archive.write(
                        evidence_path,
                        arcname=f"02_Evidence/{package_filename}",
                    )
                    manifest_items.append(
                        _manifest_item(
                            sequence_number=sequence_number,
                            evidence=evidence,
                            risk_record=risk_record,
                            package_filename=package_filename,
                            file_path=evidence_path,
                        )
                    )

                package_metadata = {
                    "risk_record_id": str(risk_record.id),
                    "risk_id": risk_record.risk_id,
                    "generated_at_utc": _format_datetime(generated_at),
                    "generated_by_user_id": str(user.id),
                    "include_archived": include_archived,
                    "include_risk_dossier": include_risk_dossier,
                    "evidence_count": len(manifest_items),
                    "total_evidence_size_bytes": sum(
                        item["file_size_bytes"] for item in manifest_items
                    ),
                }
                archive.writestr(
                    "03_Manifest/evidence_manifest.csv",
                    _manifest_csv(manifest_items),
                )
                archive.writestr(
                    "03_Manifest/evidence_manifest.json",
                    json.dumps(
                        {
                            "package_metadata": package_metadata,
                            "evidence_items": manifest_items,
                        },
                        default=_json_safe,
                        ensure_ascii=True,
                        indent=2,
                    ),
                )
                archive.writestr(
                    "03_Manifest/package_readme.txt",
                    _package_readme(
                        risk_record=risk_record,
                        generated_at=generated_at,
                        generated_by_user_id=user.id,
                        include_archived=include_archived,
                        include_risk_dossier=include_risk_dossier,
                        evidence_count=len(manifest_items),
                    ),
                )
    except Exception as exc:
        file_path.unlink(missing_ok=True)
        if isinstance(exc, RiskEvidencePackageBusinessRuleError):
            raise
        raise RiskEvidencePackageBusinessRuleError(
            "Failed to generate Risk Evidence Package ZIP"
        ) from exc

    return file_path
