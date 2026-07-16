import json

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import DEVELOPMENT_JWT_SECRET, Settings, settings
from app.main import app


SAFE_PRODUCTION_SETTINGS = {
    "environment": "production",
    "jwt_secret_key": "replace-with-a-long-random-secret-32-plus-chars",
    "enable_x_user_id_auth_fallback": False,
    "cors_allowed_origins": "https://risk-tool.example.com",
    "database_url": (
        "postgresql+psycopg://risk_user:strong_password@db.example.com:5432/"
        "risk_db"
    ),
    "evidence_storage_dir": "/var/lib/aviation-risk/evidence_uploads",
    "generated_reports_dir": "/var/lib/aviation-risk/generated_reports",
}


def _production_settings(**overrides: object) -> Settings:
    data = {**SAFE_PRODUCTION_SETTINGS, **overrides}
    return Settings(**data)


def test_default_development_settings_do_not_raise() -> None:
    Settings().validate_production_safety()


def test_production_rejects_default_development_jwt_secret() -> None:
    production = _production_settings(jwt_secret_key=DEVELOPMENT_JWT_SECRET)

    with pytest.raises(ValueError, match="JWT Secret"):
        production.validate_production_safety()


def test_production_rejects_short_jwt_secret() -> None:
    production = _production_settings(jwt_secret_key="short")

    with pytest.raises(ValueError, match="at least 32"):
        production.validate_production_safety()


def test_production_rejects_development_authentication_fallback() -> None:
    production = _production_settings(enable_x_user_id_auth_fallback=True)

    with pytest.raises(ValueError, match="Development Authentication Fallback"):
        production.validate_production_safety()


def test_production_rejects_wildcard_cors_origin() -> None:
    production = _production_settings(cors_allowed_origins="*")

    with pytest.raises(ValueError, match="CORS Allowed Origins"):
        production.validate_production_safety()


def test_production_rejects_blank_cors_origin() -> None:
    production = _production_settings(cors_allowed_origins=" ")

    with pytest.raises(ValueError, match="CORS Allowed Origins"):
        production.validate_production_safety()


def test_production_rejects_localhost_cors_by_default() -> None:
    production = _production_settings(cors_allowed_origins="http://localhost:5174")

    with pytest.raises(ValueError, match="localhost"):
        production.validate_production_safety()


def test_production_allows_localhost_cors_only_when_explicitly_allowed() -> None:
    production = _production_settings(
        cors_allowed_origins="http://localhost:5174",
        allow_localhost_cors_in_production=True,
    )

    production.validate_production_safety()


def test_production_rejects_sqlite_database_url() -> None:
    production = _production_settings(database_url="sqlite+pysqlite:///:memory:")

    with pytest.raises(ValueError, match="SQLite"):
        production.validate_production_safety()


def test_production_accepts_safe_production_like_configuration() -> None:
    _production_settings().validate_production_safety()


def test_health_still_works() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "aviation-risk-management-tool",
    }


def test_readiness_returns_safe_non_secret_data() -> None:
    client = TestClient(app)

    response = client.get("/health/readiness")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["app_name"] == settings.app_name
    assert body["environment"] == settings.environment
    assert body["database_configured"] is True
    assert body["cors_origins_count"] == len(settings.cors_origins_list)
    assert body["evidence_storage_configured"] is True
    assert body["generated_reports_configured"] is True
    assert body["auth_fallback_enabled"] == settings.enable_x_user_id_auth_fallback
    assert body["production_safety_enforced"] == (
        settings.is_production and settings.require_secure_production_settings
    )


def test_readiness_does_not_expose_jwt_secret() -> None:
    client = TestClient(app)

    response = client.get("/health/readiness")
    payload = json.dumps(response.json())

    assert settings.jwt_secret_key not in payload
    assert "jwt_secret" not in payload.lower()


def test_readiness_does_not_expose_database_url() -> None:
    client = TestClient(app)

    response = client.get("/health/readiness")
    payload = json.dumps(response.json())

    assert settings.database_url not in payload
    assert "database_url" not in payload.lower()


def test_app_startup_calls_production_safety_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FakeSettings:
        app_name = "deployment-readiness-test"
        cors_origins_list = ["https://risk-tool.example.com"]

        def validate_production_safety(self) -> None:
            calls.append("called")

    monkeypatch.setattr(main_module, "settings", FakeSettings())

    main_module.create_app()

    assert calls == ["called"]
