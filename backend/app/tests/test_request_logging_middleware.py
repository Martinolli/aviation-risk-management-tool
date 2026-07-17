import logging

from fastapi.testclient import TestClient

from app.main import create_app


def test_request_without_request_id_gets_generated_response_header() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_request_with_request_id_returns_same_response_header() -> None:
    with TestClient(create_app()) as client:
        response = client.get(
            "/health",
            headers={"X-Request-ID": "manual-test-001"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "manual-test-001"


def test_health_response_still_works() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.json() == {
        "status": "ok",
        "service": "aviation-risk-management-tool",
    }


def test_readiness_includes_logging_fields() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health/readiness")

    body = response.json()
    assert body["logging_configured"] is True
    assert body["log_level"] == "INFO"
    assert body["log_format"] in {"plain", "json"}
    assert body["request_logging_enabled"] is True
    assert body["request_id_header"] == "X-Request-ID"


def test_request_logging_does_not_include_authorization_or_body(caplog) -> None:
    app = create_app()

    @app.post("/logging-body-check")
    def body_check() -> dict[str, str]:
        return {"status": "ok"}

    with caplog.at_level(logging.INFO, logger="app.request"):
        with TestClient(app) as client:
            response = client.post(
                "/logging-body-check",
                headers={
                    "Authorization": "Bearer should-not-appear",
                    "X-Request-ID": "safe-log-test",
                },
                json={"password": "should-not-appear"},
            )

    assert response.status_code == 200
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "safe-log-test" not in log_text
    assert "Authorization" not in log_text
    assert "should-not-appear" not in log_text
    assert "password" not in log_text
    assert "logging-body-check" in log_text


def test_unhandled_exception_log_includes_request_id(caplog) -> None:
    app = create_app()

    @app.get("/unexpected-logging-error")
    def unexpected_error() -> None:
        raise RuntimeError("Sensitive implementation detail")

    with caplog.at_level(logging.ERROR):
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/unexpected-logging-error",
                headers={"X-Request-ID": "error-request-001"},
            )

    assert response.status_code == 500
    assert any(
        getattr(record, "request_id", None) == "error-request-001"
        for record in caplog.records
    )


def test_api_error_response_does_not_expose_stack_trace() -> None:
    app = create_app()

    @app.get("/unexpected-safe-error")
    def unexpected_error() -> None:
        raise RuntimeError("Sensitive implementation detail")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected-safe-error")

    payload = response.json()
    assert response.status_code == 500
    assert payload == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
            "details": {},
        }
    }
    assert "Sensitive implementation detail" not in str(payload)
    assert "Traceback" not in str(payload)


def test_existing_error_response_format_remains_unchanged() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/auth/me")

    assert response.status_code == 401
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message", "details"}


def test_middleware_does_not_break_cors() -> None:
    with TestClient(create_app()) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5174",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5174"
    assert response.headers["X-Request-ID"]
