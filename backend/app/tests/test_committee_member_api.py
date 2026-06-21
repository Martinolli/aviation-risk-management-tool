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


def _committee(db: Session) -> Committee:
    committee = Committee(name=f"Committee {uuid.uuid4()}", authority_level=AuthorityLevel.LOW, committee_type=CommitteeType.OPERATIONAL_BOARD, is_active=True)
    db.add(committee)
    db.commit()
    db.refresh(committee)
    return committee


def _user(db: Session) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", display_name="Committee User", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _admin_headers(db: Session) -> dict[str, str]:
    admin = _user(db)
    committee = Committee(name=f"Governance {uuid.uuid4()}", authority_level=AuthorityLevel.MIDDLE, committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE, is_fixed=True, is_active=True)
    db.add(committee)
    db.flush()
    db.add(CommitteeMember(committee_id=committee.id, user_id=admin.id, is_active=True))
    db.commit()
    return {"X-User-Id": str(admin.id)}


def test_committee_member_crud_duplicate_and_filters(client: TestClient, db_session: Session) -> None:
    committee, user = _committee(db_session), _user(db_session)
    headers = _admin_headers(db_session)
    payload = {"committee_id": str(committee.id), "user_id": str(user.id), "role_label": "Chair"}
    create_response = client.post("/committee-members", json=payload, headers=headers)
    member_id = create_response.json()["id"]

    assert create_response.status_code == 201
    assert client.get(f"/committee-members?committee_id={committee.id}").json()[0]["id"] == member_id
    assert client.get(f"/committee-members?user_id={user.id}").json()[0]["id"] == member_id
    assert client.get(f"/committee-members/{member_id}").status_code == 200
    assert client.get(f"/committee-members/{uuid.uuid4()}").status_code == 404
    assert client.patch(f"/committee-members/{member_id}", json={"role_label": "Secretary"}, headers=headers).json()["role_label"] == "Secretary"
    assert client.post("/committee-members", json=payload, headers=headers).status_code == 400


def test_committee_member_writes_require_governance_admin(client: TestClient, db_session: Session) -> None:
    committee, user = _committee(db_session), _user(db_session)
    payload = {"committee_id": str(committee.id), "user_id": str(user.id)}
    assert client.post("/committee-members", json=payload).status_code == 400
    assert client.post("/committee-members", json=payload, headers=_admin_headers(db_session)).status_code == 201
