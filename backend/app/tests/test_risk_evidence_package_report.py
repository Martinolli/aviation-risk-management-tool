import csv
import hashlib
import io
import json
import uuid
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.enums import (
    AuditAction,
    RiskDomain,
    RiskLifecycleStatus,
    RiskWorkflowStatus,
)
from app.models.risk import RiskEvidence, RiskRecord
from app.models.user import User
from app.services.report_tracking_service import (
    RISK_EVIDENCE_PACKAGE_REPORT_TYPE,
    ReportTrackingBusinessRuleError,
    generate_and_track_risk_evidence_package,
)
from app.services.risk_evidence_package_service import (
    generate_risk_evidence_package_zip,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with SessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def evidence_storage(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    storage = tmp_path / "evidence-storage"
    monkeypatch.setattr(settings, "evidence_storage_dir", str(storage))
    storage.mkdir()
    return storage


def _create_user(db: Session) -> User:
    user = User(
        email=f"evidence-package-{uuid.uuid4()}@example.com",
        display_name="Evidence Package User",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _create_risk(db: Session, *, creator: User, is_active: bool = True) -> RiskRecord:
    risk = RiskRecord(
        risk_id=f"RISK-{uuid.uuid4().hex[:8]}",
        problem_description="Risk evidence package test",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id,
        is_active=is_active,
    )
    db.add(risk)
    db.flush()
    return risk


def _create_evidence(
    db: Session,
    *,
    risk: RiskRecord,
    storage: Path,
    filename: str,
    content: bytes,
    is_active: bool = True,
    outside_storage: bool = False,
) -> RiskEvidence:
    file_directory = (
        storage.parent / "outside-storage"
        if outside_storage
        else storage / str(risk.id)
    )
    file_directory.mkdir(parents=True, exist_ok=True)
    file_path = file_directory / f"{uuid.uuid4()}_stored.bin"
    file_path.write_bytes(content)
    evidence = RiskEvidence(
        risk_record_id=risk.id,
        original_filename=filename,
        stored_filename=file_path.name,
        storage_path=str(file_path),
        content_type="text/plain",
        file_size_bytes=len(content),
        description=f"Metadata for {filename}",
        uploaded_by_user_id=risk.created_by_user_id,
        uploaded_at=datetime.now(timezone.utc),
        is_active=is_active,
        archived_at=None if is_active else datetime.now(timezone.utc),
        archive_reason=None if is_active else "Superseded evidence",
    )
    db.add(evidence)
    db.flush()
    return evidence


def _headers(user: User) -> dict[str, str]:
    return {"X-User-Id": str(user.id)}


def _manifest_json(archive: ZipFile) -> dict:
    return json.loads(archive.read("03_Manifest/evidence_manifest.json"))


def test_authorized_user_generates_tracked_evidence_package_with_manifests(
    db_session: Session,
    evidence_storage: Path,
    tmp_path: Path,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    active_content = b"active supporting evidence"
    active = _create_evidence(
        db_session,
        risk=risk,
        storage=evidence_storage,
        filename="../active inspection report.txt",
        content=active_content,
    )
    archived = _create_evidence(
        db_session,
        risk=risk,
        storage=evidence_storage,
        filename="archived.txt",
        content=b"archived evidence",
        is_active=False,
    )

    report = generate_and_track_risk_evidence_package(
        db_session,
        risk_record_id=risk.id,
        output_dir=tmp_path / "packages",
        generated_by_user_id=user.id,
    )
    audit_log = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == risk.id,
            AuditLog.action == AuditAction.GENERATE_REPORT,
        )
    )

    assert report.report_type == RISK_EVIDENCE_PACKAGE_REPORT_TYPE
    assert report.risk_record_id == risk.id
    assert report.committee_id is None
    assert report.file_path.endswith(".zip")
    assert Path(report.file_path).is_file()
    assert audit_log is not None
    assert audit_log.new_value["report_type"] == RISK_EVIDENCE_PACKAGE_REPORT_TYPE

    with ZipFile(report.file_path) as archive:
        names = archive.namelist()
        assert "01_Risk_Dossier/" in names
        assert any(name.endswith("_risk_dossier.docx") for name in names)
        assert "02_Evidence/" in names
        assert "03_Manifest/evidence_manifest.csv" in names
        assert "03_Manifest/evidence_manifest.json" in names
        assert "03_Manifest/package_readme.txt" in names

        evidence_names = [
            name
            for name in names
            if name.startswith("02_Evidence/") and not name.endswith("/")
        ]
        assert evidence_names == ["02_Evidence/001_active_inspection_report.txt"]
        assert ".." not in evidence_names[0]
        assert archived.original_filename not in "\n".join(names)
        assert archive.read(evidence_names[0]) == active_content

        csv_rows = list(
            csv.DictReader(
                io.StringIO(
                    archive.read("03_Manifest/evidence_manifest.csv").decode()
                )
            )
        )
        assert csv_rows[0]["evidence_id"] == str(active.id)
        assert csv_rows[0]["original_filename"] == active.original_filename
        assert csv_rows[0]["uploaded_at"]
        assert csv_rows[0]["is_active"] == "True"
        assert csv_rows[0]["sha256"] == hashlib.sha256(active_content).hexdigest()

        manifest = _manifest_json(archive)
        assert manifest["package_metadata"]["evidence_count"] == 1
        assert manifest["package_metadata"]["include_archived"] is False
        assert manifest["evidence_items"][0]["evidence_id"] == str(active.id)
        assert manifest["evidence_items"][0]["sha256"] == hashlib.sha256(
            archive.read(evidence_names[0])
        ).hexdigest()
        readme = archive.read("03_Manifest/package_readme.txt").decode()
        assert "Risk Evidence Package" in readme
        assert "Controlled Export" in readme
        assert "does not replace formal committee decision entry" in readme


def test_archived_evidence_is_included_only_when_requested(
    db_session: Session,
    evidence_storage: Path,
    tmp_path: Path,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    _create_evidence(
        db_session,
        risk=risk,
        storage=evidence_storage,
        filename="active.txt",
        content=b"active",
    )
    archived = _create_evidence(
        db_session,
        risk=risk,
        storage=evidence_storage,
        filename="archived.txt",
        content=b"archived",
        is_active=False,
    )

    package_path = generate_risk_evidence_package_zip(
        db_session,
        risk_record_id=risk.id,
        generated_by_user_id=user.id,
        output_dir=tmp_path / "with-archived",
        include_archived=True,
    )

    with ZipFile(package_path) as archive:
        manifest = _manifest_json(archive)
        assert manifest["package_metadata"]["evidence_count"] == 2
        archived_item = next(
            item
            for item in manifest["evidence_items"]
            if item["evidence_id"] == str(archived.id)
        )
        assert archived_item["is_active"] is False
        assert archived_item["archive_reason"] == "Superseded evidence"


def test_package_without_evidence_still_contains_dossier_manifest_and_readme(
    db_session: Session,
    evidence_storage: Path,
    tmp_path: Path,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)

    package_path = generate_risk_evidence_package_zip(
        db_session,
        risk_record_id=risk.id,
        generated_by_user_id=user.id,
        output_dir=tmp_path / "empty-package",
    )

    with ZipFile(package_path) as archive:
        names = archive.namelist()
        assert any(name.endswith("_risk_dossier.docx") for name in names)
        assert "03_Manifest/evidence_manifest.csv" in names
        assert "03_Manifest/package_readme.txt" in names
        assert _manifest_json(archive)["package_metadata"]["evidence_count"] == 0


def test_package_can_omit_risk_dossier(
    db_session: Session,
    evidence_storage: Path,
    tmp_path: Path,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)

    package_path = generate_risk_evidence_package_zip(
        db_session,
        risk_record_id=risk.id,
        generated_by_user_id=user.id,
        output_dir=tmp_path / "without-dossier",
        include_risk_dossier=False,
    )

    with ZipFile(package_path) as archive:
        names = archive.namelist()
        assert not any(name.endswith(".docx") for name in names)
        assert "03_Manifest/evidence_manifest.json" in names
        assert "03_Manifest/package_readme.txt" in names
        assert (
            _manifest_json(archive)["package_metadata"]["include_risk_dossier"]
            is False
        )


def test_invalid_or_outside_storage_evidence_is_not_packaged(
    db_session: Session,
    evidence_storage: Path,
    tmp_path: Path,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    _create_evidence(
        db_session,
        risk=risk,
        storage=evidence_storage,
        filename="outside.txt",
        content=b"must not leak",
        outside_storage=True,
    )

    package_path = generate_risk_evidence_package_zip(
        db_session,
        risk_record_id=risk.id,
        generated_by_user_id=user.id,
        output_dir=tmp_path / "safe-package",
        include_risk_dossier=False,
    )

    with ZipFile(package_path) as archive:
        assert _manifest_json(archive)["package_metadata"]["evidence_count"] == 0
        assert not any(
            name.startswith("02_Evidence/") and not name.endswith("/")
            for name in archive.namelist()
        )


def test_evidence_package_api_authorizes_generation_and_zip_download(
    client: TestClient,
    db_session: Session,
    evidence_storage: Path,
    tmp_path: Path,
) -> None:
    creator = _create_user(db_session)
    unauthorized = _create_user(db_session)
    risk = _create_risk(db_session, creator=creator)
    _create_evidence(
        db_session,
        risk=risk,
        storage=evidence_storage,
        filename="support.txt",
        content=b"support",
    )
    db_session.commit()

    unauthorized_generation = client.post(
        f"/reports/risk-evidence-packages/{risk.id}",
        headers=_headers(unauthorized),
        json={"output_dir": str(tmp_path / "unauthorized")},
    )
    created = client.post(
        f"/reports/risk-evidence-packages/{risk.id}",
        headers=_headers(creator),
        json={
            "output_dir": str(tmp_path / "authorized"),
            "include_archived": False,
            "include_risk_dossier": True,
        },
    )

    assert unauthorized_generation.status_code == 400
    assert created.status_code == 201
    report = created.json()
    assert report["report_type"] == RISK_EVIDENCE_PACKAGE_REPORT_TYPE
    assert report["risk_record_id"] == str(risk.id)
    assert report["committee_id"] is None

    authorized_download = client.get(
        f"/reports/{report['id']}/download",
        headers=_headers(creator),
    )
    unauthorized_download = client.get(
        f"/reports/{report['id']}/download",
        headers=_headers(unauthorized),
    )

    assert authorized_download.status_code == 200
    assert authorized_download.headers["content-type"] == "application/zip"
    assert authorized_download.content.startswith(b"PK")
    assert unauthorized_download.status_code == 400


def test_inactive_risk_cannot_generate_evidence_package(
    db_session: Session,
    evidence_storage: Path,
    tmp_path: Path,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user, is_active=False)

    with pytest.raises(ReportTrackingBusinessRuleError, match="inactive"):
        generate_and_track_risk_evidence_package(
            db_session,
            risk_record_id=risk.id,
            output_dir=tmp_path,
            generated_by_user_id=user.id,
        )
