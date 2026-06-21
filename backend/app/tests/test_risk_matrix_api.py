import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from app.models.committee import Committee, CommitteeMember
from app.models.enums import AuthorityLevel, CommitteeType
from app.models.user import User
from app.services.security_service import hash_password


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
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


def _user(db: Session, *, password: bool = False) -> User:
    user = User(email=f"matrix-{uuid.uuid4()}@example.com", display_name="Matrix User", password_hash=hash_password("StrongPassword123!") if password else None, is_active=True)
    db.add(user)
    db.flush()
    return user


def _admin_headers(db: Session) -> dict[str, str]:
    user = _user(db)
    committee = Committee(name=f"Governance {uuid.uuid4()}", authority_level=AuthorityLevel.MIDDLE, committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE, is_fixed=True, is_active=True)
    db.add(committee)
    db.flush()
    db.add(CommitteeMember(committee_id=committee.id, user_id=user.id, is_active=True))
    db.commit()
    return {"X-User-Id": str(user.id)}


def _reference_payload(code: str, name: str, numeric_value: int) -> dict[str, object]:
    return {"code": code, "name": name, "numeric_value": numeric_value}


def test_matrix_api_requires_authenticated_reads_and_governance_writes(client: TestClient, db_session: Session) -> None:
    assert client.get("/risk-matrix/severity-levels").status_code == 401
    regular = _user(db_session)
    db_session.commit()
    assert client.get("/risk-matrix/severity-levels", headers={"X-User-Id": str(regular.id)}).status_code == 200
    assert client.post("/risk-matrix/severity-levels", json=_reference_payload("S1", "Negligible", 1), headers={"X-User-Id": str(regular.id)}).status_code == 400


def test_governance_admin_can_configure_and_archive_matrix_cells(client: TestClient, db_session: Session) -> None:
    headers = _admin_headers(db_session)
    severity = client.post("/risk-matrix/severity-levels", json=_reference_payload(" s3 ", "Major", 3), headers=headers)
    likelihood = client.post("/risk-matrix/likelihood-levels", json=_reference_payload("l2", "Remote", 2), headers=headers)
    risk_level = client.post("/risk-matrix/risk-levels", json=_reference_payload("high", "High", 3), headers=headers)

    assert severity.status_code == likelihood.status_code == risk_level.status_code == 201
    assert severity.json()["code"] == "S3"
    cell = client.post("/risk-matrix/cells", json={"severity_level_id": severity.json()["id"], "likelihood_level_id": likelihood.json()["id"], "risk_level_id": risk_level.json()["id"]}, headers=headers)
    assert cell.status_code == 201
    assert cell.json()["score"] == 6
    assert client.post("/risk-matrix/cells", json={"severity_level_id": severity.json()["id"], "likelihood_level_id": likelihood.json()["id"], "risk_level_id": risk_level.json()["id"]}, headers=headers).status_code == 400
    assert client.patch(f"/risk-matrix/severity-levels/{severity.json()['id']}", json={"name": "Major Safety Risk"}, headers=headers).status_code == 200
    archive = client.post(f"/risk-matrix/cells/{cell.json()['id']}/archive", headers=headers)
    assert archive.status_code == 200
    assert archive.json()["is_active"] is False
    assert client.get(f"/risk-matrix/cells/{uuid.uuid4()}", headers=headers).status_code == 404


def test_matrix_api_accepts_bearer_governance_admin(client: TestClient, db_session: Session) -> None:
    admin = _user(db_session, password=True)
    committee = Committee(name=f"Governance {uuid.uuid4()}", authority_level=AuthorityLevel.HIGH, committee_type=CommitteeType.EXECUTIVE_SAFETY_MANAGEMENT_COMMITTEE, is_fixed=True, is_active=True)
    db_session.add(committee)
    db_session.flush()
    db_session.add(CommitteeMember(committee_id=committee.id, user_id=admin.id, is_active=True))
    db_session.commit()
    login = client.post("/auth/login", json={"email": admin.email, "password": "StrongPassword123!"})

    response = client.post("/risk-matrix/severity-levels", json=_reference_payload("S1", "Negligible", 1), headers={"Authorization": f"Bearer {login.json()['access_token']}"})

    assert login.status_code == 200
    assert response.status_code == 201
