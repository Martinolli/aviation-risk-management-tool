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


def test_user_crud_and_duplicate_email(client: TestClient) -> None:
    create_response = client.post("/users", json=_payload("avery@example.com"))
    user_id = create_response.json()["id"]

    assert create_response.status_code == 201
    assert client.get("/users").json()[0]["id"] == user_id
    assert client.get(f"/users/{user_id}").status_code == 200
    assert client.get(f"/users/{uuid.uuid4()}").status_code == 404
    assert client.patch(f"/users/{user_id}", json={"display_name": "Avery Test Pilot"}).json()["display_name"] == "Avery Test Pilot"
    assert client.post("/users", json=_payload("AVERY@example.com")).status_code == 400
