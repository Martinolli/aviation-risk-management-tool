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
from app.models.committee import Committee
from app.models.enums import AuthorityLevel, CommitteeType


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


def _name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"


def _create_committee(
    db_session: Session,
    *,
    name: str,
    authority_level: AuthorityLevel = AuthorityLevel.LOW,
    committee_type: CommitteeType = CommitteeType.OPERATIONAL_BOARD,
    is_fixed: bool = False,
) -> Committee:
    committee = Committee(
        name=name,
        authority_level=authority_level,
        committee_type=committee_type,
        is_fixed=is_fixed,
        is_active=True,
    )
    db_session.add(committee)
    db_session.commit()
    db_session.refresh(committee)
    return committee


def test_get_committees_returns_list(
    client: TestClient,
    db_session: Session,
) -> None:
    _create_committee(db_session, name=_name("Flight Test Safety Committee"))

    response = client.get("/committees")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_post_committees_with_low_operational_board_returns_created_committee(
    client: TestClient,
) -> None:
    payload = {
        "name": _name("Aircraft Safety Committee"),
        "description": "Engineering board",
        "authority_level": "LOW",
        "committee_type": "OPERATIONAL_BOARD",
    }

    response = client.post("/committees", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["authority_level"] == "LOW"
    assert body["committee_type"] == "OPERATIONAL_BOARD"
    assert body["is_fixed"] is False


def test_post_committees_with_middle_returns_http_400(
    client: TestClient,
) -> None:
    response = client.post(
        "/committees",
        json={
            "name": _name("Risk Management Committee"),
            "description": None,
            "authority_level": "MIDDLE",
            "committee_type": "RISK_MANAGEMENT_COMMITTEE",
        },
    )

    assert response.status_code == 400


def test_patch_committee_updates_low_committee(
    client: TestClient,
    db_session: Session,
) -> None:
    committee = _create_committee(db_session, name=_name("Industrial Safety Committee"))
    new_name = _name("Industrial Safety Board")

    response = client.patch(f"/committees/{committee.id}", json={"name": new_name})

    assert response.status_code == 200
    assert response.json()["name"] == new_name


def test_archive_low_committee(
    client: TestClient,
    db_session: Session,
) -> None:
    committee = _create_committee(db_session, name=_name("Quality Safety Committee"))

    response = client.post(
        f"/committees/{committee.id}/archive",
        json={"archive_reason": "No longer active"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["archive_reason"] == "No longer active"
    assert body["archived_at"] is not None


def test_archive_fixed_committee_returns_http_400(
    client: TestClient,
    db_session: Session,
) -> None:
    committee = _create_committee(
        db_session,
        name=_name("Risk Management Committee"),
        authority_level=AuthorityLevel.MIDDLE,
        committee_type=CommitteeType.RISK_MANAGEMENT_COMMITTEE,
        is_fixed=True,
    )

    response = client.post(
        f"/committees/{committee.id}/archive",
        json={"archive_reason": "Attempted archive"},
    )

    assert response.status_code == 400


def test_get_unknown_committee_returns_http_404(client: TestClient) -> None:
    response = client.get(f"/committees/{uuid.uuid4()}")

    assert response.status_code == 404
