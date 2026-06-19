import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.enums import RiskDomain, RiskLifecycleStatus, RiskWorkflowStatus
from app.models.risk import RiskRecord


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


def _create_risk_record(
    db_session: Session,
    *,
    risk_id: str = "RISK-2026-0001",
) -> RiskRecord:
    risk_record = RiskRecord(
        risk_id=risk_id,
        problem_description=f"Risk record {uuid.uuid4()}",
        domain=RiskDomain.FLIGHT_TEST,
        workflow_status=RiskWorkflowStatus.DRAFT,
        lifecycle_status=RiskLifecycleStatus.OPEN,
        is_active=True,
    )
    db_session.add(risk_record)
    db_session.commit()
    db_session.refresh(risk_record)
    return risk_record


def _post_report(
    client: TestClient,
    risk_record_id: uuid.UUID,
    output_dir: Path,
):
    return client.post(
        f"/reports/risk-dossiers/{risk_record_id}",
        json={"output_dir": str(output_dir)},
    )


def test_post_risk_dossier_report_returns_201(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = _post_report(client, risk_record.id, tmp_path)

    assert response.status_code == 201


def test_post_risk_dossier_report_creates_report_metadata(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = _post_report(client, risk_record.id, tmp_path)

    assert response.status_code == 201
    body = response.json()
    assert body["risk_record_id"] == str(risk_record.id)
    assert body["report_type"] == "RISK_DOSSIER_DOCX"
    assert body["file_path"]


def test_post_risk_dossier_report_creates_physical_docx_file(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)

    response = _post_report(client, risk_record.id, tmp_path)

    assert response.status_code == 201
    assert Path(response.json()["file_path"]).is_file()


def test_post_unknown_risk_returns_http_400(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = _post_report(client, uuid.uuid4(), tmp_path)

    assert response.status_code == 400


def test_get_reports_returns_list(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    _post_report(client, risk_record.id, tmp_path)

    response = client.get("/reports")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_reports_filters_by_risk_record_id(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    first_risk = _create_risk_record(db_session, risk_id="RISK-2026-0001")
    second_risk = _create_risk_record(db_session, risk_id="RISK-2026-0002")
    first_response = _post_report(client, first_risk.id, tmp_path)
    _post_report(client, second_risk.id, tmp_path)

    response = client.get(f"/reports?risk_record_id={first_risk.id}")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == first_response.json()["id"]


def test_get_reports_filters_by_report_type(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    report_response = _post_report(client, risk_record.id, tmp_path)

    response = client.get("/reports?report_type=RISK_DOSSIER_DOCX")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == report_response.json()["id"]


def test_get_report_returns_report(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
) -> None:
    risk_record = _create_risk_record(db_session)
    report_response = _post_report(client, risk_record.id, tmp_path)

    response = client.get(f"/reports/{report_response.json()['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == report_response.json()["id"]


def test_get_unknown_report_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/reports/{uuid.uuid4()}")

    assert response.status_code == 404
