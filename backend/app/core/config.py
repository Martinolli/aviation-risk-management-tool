from functools import lru_cache
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEVELOPMENT_JWT_SECRET = "dev-change-me-use-env-secret-in-production-32bytes"
ALLOWED_ENVIRONMENTS = {"development", "test", "production"}
LOCALHOST_CORS_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0"}
ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
ALLOWED_LOG_FORMATS = {"plain", "json"}


class Settings(BaseSettings):
    app_name: str = "aviation-risk-management-tool"
    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
        "aviation_risk_management"
    )
    # Production deployments must override this development-only value.
    jwt_secret_key: str = DEVELOPMENT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    enable_x_user_id_auth_fallback: bool = False
    cors_allowed_origins: str = (
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    allow_localhost_cors_in_production: bool = False
    frontend_base_url: str = "http://localhost:5174"
    backend_base_url: str = "http://127.0.0.1:8000"
    evidence_storage_dir: str = "backend/evidence_uploads"
    generated_reports_dir: str = "backend/generated_reports"
    max_evidence_upload_mb: int = 25
    require_secure_production_settings: bool = True
    log_level: str = "INFO"
    log_format: str = "plain"
    enable_request_logging: bool = True
    log_request_headers: bool = False
    log_response_status: bool = True
    log_request_duration: bool = True
    request_id_header: str = "X-Request-ID"
    allow_debug_logging_in_production: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        environment = value.strip().lower()
        if environment not in ALLOWED_ENVIRONMENTS:
            allowed = ", ".join(sorted(ALLOWED_ENVIRONMENTS))
            raise ValueError(f"ENVIRONMENT must be one of: {allowed}.")
        return environment

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        log_level = value.strip().upper()
        if log_level not in ALLOWED_LOG_LEVELS:
            allowed = ", ".join(sorted(ALLOWED_LOG_LEVELS))
            raise ValueError(f"LOG_LEVEL must be one of: {allowed}.")
        return log_level

    @field_validator("log_format")
    @classmethod
    def _validate_log_format(cls, value: str) -> str:
        log_format = value.strip().lower()
        if log_format not in ALLOWED_LOG_FORMATS:
            allowed = ", ".join(sorted(ALLOWED_LOG_FORMATS))
            raise ValueError(f"LOG_FORMAT must be one of: {allowed}.")
        return log_format

    @property
    def cors_origins_list(self) -> list[str]:
        """Return configured CORS origins after trimming empty values."""
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def max_evidence_upload_bytes(self) -> int:
        return self.max_evidence_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def normalized_log_level(self) -> str:
        return self.log_level

    @property
    def is_json_logging(self) -> bool:
        return self.log_format == "json"

    def validate_production_safety(self) -> None:
        if not self.is_production:
            return
        if not self.require_secure_production_settings:
            raise ValueError(
                "Production Configuration requires "
                "REQUIRE_SECURE_PRODUCTION_SETTINGS=true."
            )

        errors: list[str] = []
        if self.jwt_secret_key == DEVELOPMENT_JWT_SECRET:
            errors.append(
                "JWT Secret must be changed from the development default."
            )
        if len(self.jwt_secret_key) < 32:
            errors.append("JWT Secret must be at least 32 characters long.")
        if self.enable_x_user_id_auth_fallback:
            errors.append(
                "Development Authentication Fallback must be disabled in production."
            )
        if (
            self.normalized_log_level == "DEBUG"
            and not self.allow_debug_logging_in_production
        ):
            errors.append(
                "DEBUG logging must not be enabled in production unless "
                "ALLOW_DEBUG_LOGGING_IN_PRODUCTION=true."
            )

        origins = self.cors_origins_list
        raw_origins = self.cors_allowed_origins.split(",")
        if not origins:
            errors.append("CORS Allowed Origins must not be blank in production.")
        if any(not origin.strip() for origin in raw_origins):
            errors.append(
                "CORS Allowed Origins must contain only explicit non-blank origins."
            )
        if "*" in origins:
            errors.append("CORS Allowed Origins must not include '*' in production.")
        if (
            not self.allow_localhost_cors_in_production
            and _has_localhost_origin(origins)
        ):
            errors.append(
                "CORS Allowed Origins must not include localhost, 127.0.0.1, "
                "or 0.0.0.0 in production unless "
                "ALLOW_LOCALHOST_CORS_IN_PRODUCTION=true."
            )

        database_url = self.database_url.strip()
        if not database_url:
            errors.append("DATABASE_URL must be configured in production.")
        if database_url.lower().startswith("sqlite"):
            errors.append("DATABASE_URL must not use SQLite in production.")
        if _uses_default_local_postgres_credentials(database_url):
            errors.append(
                "DATABASE_URL must not use local PostgreSQL default credentials "
                "or postgres:postgres in production."
            )

        if not self.evidence_storage_dir.strip():
            errors.append("Evidence Storage path must not be blank in production.")
        if not self.generated_reports_dir.strip():
            errors.append("Generated Reports path must not be blank in production.")

        if errors:
            message = "Production Configuration failed Environment Hardening checks: "
            raise ValueError(message + " ".join(errors))


def _has_localhost_origin(origins: list[str]) -> bool:
    for origin in origins:
        lower_origin = origin.lower()
        if any(local_host in lower_origin for local_host in LOCALHOST_CORS_HOSTS):
            return True
        parsed = urlparse(origin)
        host = (parsed.hostname or origin).lower()
        if host in LOCALHOST_CORS_HOSTS:
            return True
    return False


def _uses_default_local_postgres_credentials(database_url: str) -> bool:
    parsed = urlparse(database_url)
    username = parsed.username or ""
    password = parsed.password or ""
    host = parsed.hostname or ""
    return (
        username == "postgres"
        and password == "postgres"
        and host in {"localhost", "127.0.0.1", "0.0.0.0", ""}
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
