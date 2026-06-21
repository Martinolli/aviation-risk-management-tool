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


def _payload(email: str | None = None) -> dict[str, str]:
    return {"email": email or f"{uuid.uuid4()}@example.com", "display_name": "Avery Pilot"}


def _admin_headers(db_session: Session, *, level: AuthorityLevel = AuthorityLevel.MIDDLE) -> dict[str, str]:
    admin = User(email=f"admin-{uuid.uuid4()}@example.com", display_name="Admin", is_active=True)
    committee = Committee(
        name=f"Governance {uuid.uuid4()}",
        authority_level=level,
        committee_type=CommitteeType.OPERATIONAL_BOARD,
        is_fixed=True,
        is_active=True,
    )
    db_session.add_all([admin, committee])
    db_session.flush()
    db_session.add(CommitteeMember(committee_id=committee.id, user_id=admin.id, is_active=True))
    db_session.commit()
    return {"X-User-Id": str(admin.id)}


def test_user_crud_and_duplicate_email(client: TestClient, db_session: Session) -> None:
    headers = _admin_headers(db_session)
    create_response = client.post("/users", json=_payload("avery@example.com"), headers=headers)
    user_id = create_response.json()["id"]

    assert create_response.status_code == 201
    assert user_id in {user["id"] for user in client.get("/users").json()}
    assert client.get(f"/users/{user_id}").status_code == 200
    assert client.get(f"/users/{uuid.uuid4()}").status_code == 404
    assert client.patch(f"/users/{user_id}", json={"display_name": "Avery Test Pilot"}, headers=headers).json()["display_name"] == "Avery Test Pilot"
    assert client.post("/users", json=_payload("AVERY@example.com"), headers=headers).status_code == 400


def test_user_writes_require_governance_admin(client: TestClient, db_session: Session) -> None:
    assert client.post("/users", json=_payload()).status_code == 400
    regular = User(email=f"regular-{uuid.uuid4()}@example.com", display_name="Regular", is_active=True)
    db_session.add(regular)
    db_session.commit()
    assert client.post("/users", json=_payload(), headers={"X-User-Id": str(regular.id)}).status_code == 400
    assert client.post("/users", json=_payload(), headers=_admin_headers(db_session, level=AuthorityLevel.HIGH)).status_code == 201
