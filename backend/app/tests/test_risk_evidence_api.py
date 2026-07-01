import uuid
from collections.abc import Generator
from pathlib import Path

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
from app.models.enums import AuditAction, RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus
from app.models.risk import RiskEvidence, RiskRecord
from app.models.user import User
from app.services.auth_service import create_access_token


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


@pytest.fixture(autouse=True)
def temporary_evidence_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    storage_path = tmp_path / "evidence"
    monkeypatch.setattr(settings, "evidence_storage_dir", str(storage_path))
    return storage_path


def _create_user(db: Session, *, is_active: bool = True) -> User:
    user = User(
        email=f"evidence-{uuid.uuid4()}@example.com",
        display_name="Evidence User",
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_risk(
    db: Session,
    *,
    creator: User,
    is_active: bool = True,
) -> RiskRecord:
    risk = RiskRecord(
        risk_id=f"RISK-{uuid.uuid4()}",
        problem_description="Evidence API test risk",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        created_by_user_id=creator.id,
        is_active=is_active,
    )
    db.add(risk)
    db.commit()
    db.refresh(risk)
    return risk


def _headers(user: User) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user_id=user.id)}",
    }


def _upload(
    client: TestClient,
    risk: RiskRecord,
    user: User,
    *,
    filename: str = "supporting-document.txt",
    content: bytes = b"supporting evidence",
    content_type: str = "text/plain",
    description: str = "Supporting document",
):
    return client.post(
        f"/risk-evidence/{risk.id}/upload",
        headers=_headers(user),
        files={"file": (filename, content, content_type)},
        data={"description": description},
    )


def test_authorized_user_uploads_metadata_and_file(
    client: TestClient,
    db_session: Session,
    temporary_evidence_storage: Path,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)

    response = _upload(client, risk, user)

    assert response.status_code == 201
    body = response.json()
    assert body["risk_record_id"] == str(risk.id)
    assert body["original_filename"] == "supporting-document.txt"
    assert body["description"] == "Supporting document"
    assert body["file_size_bytes"] == len(b"supporting evidence")
    evidence = db_session.get(RiskEvidence, uuid.UUID(body["id"]))
    assert evidence is not None
    assert evidence.uploaded_by_user_id == user.id
    assert Path(evidence.storage_path).read_bytes() == b"supporting evidence"
    assert Path(evidence.storage_path).is_relative_to(temporary_evidence_storage)


def test_list_returns_uploaded_evidence_newest_first(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    first = _upload(client, risk, user, filename="first.txt").json()
    second = _upload(client, risk, user, filename="second.txt").json()

    response = client.get(
        f"/risk-evidence/risk/{risk.id}", headers=_headers(user)
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second["id"], first["id"]]


def test_get_and_download_return_metadata_and_original_file(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    evidence = _upload(
        client,
        risk,
        user,
        filename="flight notes.txt",
        content=b"download content",
    ).json()

    metadata = client.get(
        f"/risk-evidence/{evidence['id']}", headers=_headers(user)
    )
    download = client.get(
        f"/risk-evidence/{evidence['id']}/download", headers=_headers(user)
    )

    assert metadata.status_code == 200
    assert metadata.json()["original_filename"] == "flight notes.txt"
    assert download.status_code == 200
    assert download.content == b"download content"
    assert "flight%20notes.txt" in download.headers["content-disposition"]


def test_archive_sets_fields_and_list_filtering(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    evidence = _upload(client, risk, user).json()

    archive = client.post(
        f"/risk-evidence/{evidence['id']}/archive",
        headers=_headers(user),
        json={"archive_reason": "Superseded document"},
    )
    active_list = client.get(
        f"/risk-evidence/risk/{risk.id}", headers=_headers(user)
    )
    archived_list = client.get(
        f"/risk-evidence/risk/{risk.id}?include_archived=true",
        headers=_headers(user),
    )

    assert archive.status_code == 200
    assert archive.json()["is_active"] is False
    assert archive.json()["archived_at"] is not None
    assert archive.json()["archived_by_user_id"] == str(user.id)
    assert archive.json()["archive_reason"] == "Superseded document"
    assert active_list.json() == []
    assert [item["id"] for item in archived_list.json()] == [evidence["id"]]
    assert Path(db_session.get(RiskEvidence, uuid.UUID(evidence["id"])).storage_path).is_file()


def test_unauthenticated_user_cannot_use_evidence_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    evidence = _upload(client, risk, user).json()

    responses = [
        client.post(
            f"/risk-evidence/{risk.id}/upload",
            files={"file": ("document.txt", b"content", "text/plain")},
        ),
        client.get(f"/risk-evidence/risk/{risk.id}"),
        client.get(f"/risk-evidence/{evidence['id']}"),
        client.get(f"/risk-evidence/{evidence['id']}/download"),
        client.post(f"/risk-evidence/{evidence['id']}/archive", json={}),
    ]

    assert [response.status_code for response in responses] == [400] * 5


def test_unrelated_user_cannot_use_evidence_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    creator = _create_user(db_session)
    unrelated = _create_user(db_session)
    risk = _create_risk(db_session, creator=creator)
    evidence = _upload(client, risk, creator).json()
    headers = _headers(unrelated)

    responses = [
        client.post(
            f"/risk-evidence/{risk.id}/upload",
            headers=headers,
            files={"file": ("document.txt", b"content", "text/plain")},
        ),
        client.get(f"/risk-evidence/risk/{risk.id}", headers=headers),
        client.get(f"/risk-evidence/{evidence['id']}", headers=headers),
        client.get(
            f"/risk-evidence/{evidence['id']}/download", headers=headers
        ),
        client.post(
            f"/risk-evidence/{evidence['id']}/archive", headers=headers, json={}
        ),
    ]

    assert [response.status_code for response in responses] == [400] * 5


def test_upload_rejects_missing_filename_and_empty_file(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)

    missing_filename = client.post(
        f"/risk-evidence/{risk.id}/upload",
        headers=_headers(user),
        files={"file": ("", b"content", "text/plain")},
    )
    empty_file = _upload(client, risk, user, content=b"")

    assert missing_filename.status_code in {400, 422}
    assert empty_file.status_code == 400
    assert db_session.scalar(select(RiskEvidence)) is None


def test_upload_rejects_file_over_configured_limit(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    monkeypatch.setattr(settings, "max_evidence_upload_mb", 1)

    response = _upload(client, risk, user, content=b"x" * (1024 * 1024 + 1))

    assert response.status_code == 400
    assert "1 MB limit" in response.json()["error"]["message"]


def test_upload_rejects_dangerous_content_type_and_inactive_risk(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    active_risk = _create_risk(db_session, creator=user)
    inactive_risk = _create_risk(db_session, creator=user, is_active=False)

    dangerous = _upload(
        client,
        active_risk,
        user,
        filename="script.sh",
        content=b"echo unsafe",
        content_type="application/x-sh",
    )
    inactive = _upload(client, inactive_risk, user)

    assert dangerous.status_code == 400
    assert inactive.status_code == 400


def test_unknown_risk_and_evidence_return_404(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    headers = _headers(user)
    missing_risk = uuid.uuid4()
    missing_evidence = uuid.uuid4()

    assert client.get(
        f"/risk-evidence/risk/{missing_risk}", headers=headers
    ).status_code == 404
    assert client.post(
        f"/risk-evidence/{missing_risk}/upload",
        headers=headers,
        files={"file": ("document.txt", b"content", "text/plain")},
    ).status_code == 404
    assert client.get(
        f"/risk-evidence/{missing_evidence}", headers=headers
    ).status_code == 404
    assert client.get(
        f"/risk-evidence/{missing_evidence}/download", headers=headers
    ).status_code == 404
    assert client.post(
        f"/risk-evidence/{missing_evidence}/archive", headers=headers, json={}
    ).status_code == 404


def test_upload_and_archive_create_audit_logs(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session)
    risk = _create_risk(db_session, creator=user)
    evidence = _upload(client, risk, user).json()
    client.post(
        f"/risk-evidence/{evidence['id']}/archive",
        headers=_headers(user),
        json={"archive_reason": "No longer current"},
    )

    logs = list(
        db_session.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_type == "RiskEvidence",
                AuditLog.entity_id == uuid.UUID(evidence["id"]),
            )
            .order_by(AuditLog.changed_at)
        )
    )

    assert [log.action for log in logs] == [AuditAction.CREATE, AuditAction.ARCHIVE]
    assert logs[0].new_value["risk_record_id"] == str(risk.id)
    assert logs[0].new_value["original_filename"] == "supporting-document.txt"
    assert logs[1].reason == "No longer current"
