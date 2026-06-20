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


def test_role_crud_and_duplicate_name(client: TestClient) -> None:
    create_response = client.post("/roles", json={"name": "Chair", "description": "Leads"})
    role_id = create_response.json()["id"]

    assert create_response.status_code == 201
    assert client.get("/roles").json()[0]["id"] == role_id
    assert client.get(f"/roles/{role_id}").status_code == 200
    assert client.get(f"/roles/{uuid.uuid4()}").status_code == 404
    assert client.patch(f"/roles/{role_id}", json={"description": "Committee chair"}).json()["description"] == "Committee chair"
    assert client.post("/roles", json={"name": "chair"}).status_code == 400
