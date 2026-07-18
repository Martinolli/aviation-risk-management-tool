import json

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.version import APP_RELEASE_STATUS, APP_VERSION
from app.main import app


def test_app_version_metadata_matches_pilot_release() -> None:
    assert APP_VERSION == "1.0.0-pilot"


def test_readiness_includes_app_version() -> None:
    client = TestClient(app)

    response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["app_version"] == APP_VERSION


def test_readiness_includes_release_status() -> None:
    client = TestClient(app)

    response = client.get("/health/readiness")

    assert response.status_code == 200
    assert response.json()["release_status"] == APP_RELEASE_STATUS


def test_readiness_version_metadata_does_not_expose_secrets() -> None:
    client = TestClient(app)

    response = client.get("/health/readiness")
    payload = json.dumps(response.json())

    assert settings.jwt_secret_key not in payload
    assert settings.database_url not in payload
    assert "jwt_secret" not in payload.lower()
    assert "database_url" not in payload.lower()
