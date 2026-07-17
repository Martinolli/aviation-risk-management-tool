import json
import logging

import pytest
from pydantic import ValidationError

from app.core.config import DEVELOPMENT_JWT_SECRET, Settings
from app.core.logging_config import JsonLogFormatter, RequestIdFilter, configure_logging
from app.core.request_context import reset_request_id, set_request_id


def _production_settings(**overrides: object) -> Settings:
    data = {
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
        **overrides,
    }
    return Settings(**data)


def test_settings_accepts_info_log_level() -> None:
    settings = Settings(log_level="INFO")

    assert settings.normalized_log_level == "INFO"


def test_settings_rejects_invalid_log_level() -> None:
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings(log_level="VERBOSE")


def test_production_rejects_debug_without_explicit_allowance() -> None:
    settings = _production_settings(log_level="DEBUG")

    with pytest.raises(ValueError, match="DEBUG logging"):
        settings.validate_production_safety()


def test_production_allows_debug_only_when_explicitly_allowed() -> None:
    settings = _production_settings(
        log_level="DEBUG",
        allow_debug_logging_in_production=True,
    )

    settings.validate_production_safety()


def test_configure_logging_is_idempotent() -> None:
    settings = Settings(log_level="INFO")
    configure_logging(settings)
    configure_logging(settings)

    marked_handlers = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_aviation_risk_logging_handler", False)
    ]

    assert len(marked_handlers) == 1


def test_log_record_receives_default_request_id() -> None:
    configure_logging(Settings())

    record = logging.getLogger("app.test").makeRecord(
        "app.test",
        logging.INFO,
        __file__,
        1,
        "message",
        args=(),
        exc_info=None,
    )

    assert record.request_id == "-"


def test_json_formatter_outputs_valid_json_with_request_id() -> None:
    token = set_request_id("json-test-request")
    try:
        record = logging.getLogger("app.test").makeRecord(
            "app.test",
            logging.INFO,
            __file__,
            1,
            "JSON log message",
            args=(),
            exc_info=None,
        )
        payload = json.loads(JsonLogFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["message"] == "JSON log message"
    assert payload["request_id"] == "json-test-request"
    assert payload["level"] == "INFO"


def test_json_formatter_does_not_include_settings_secrets() -> None:
    settings = Settings()
    record = logging.getLogger("app.test").makeRecord(
        "app.test",
        logging.INFO,
        __file__,
        1,
        "Safe startup summary",
        args=(),
        exc_info=None,
    )
    payload = JsonLogFormatter().format(record)

    assert settings.jwt_secret_key not in payload
    assert settings.database_url not in payload
    assert DEVELOPMENT_JWT_SECRET not in payload
    assert "database_url" not in payload.lower()
    assert "jwt_secret" not in payload.lower()


def test_plain_formatter_can_format_record_with_request_id() -> None:
    record = logging.getLogger("app.test").makeRecord(
        "app.test",
        logging.INFO,
        __file__,
        1,
        "plain message",
        args=(),
        exc_info=None,
    )
    RequestIdFilter().filter(record)
    formatter = logging.Formatter(
        "%(levelname)s %(name)s [request_id=%(request_id)s] %(message)s"
    )

    text = formatter.format(record)

    assert "request_id=-" in text
    assert "plain message" in text
