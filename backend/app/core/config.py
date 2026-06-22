from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "aviation-risk-management-tool"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
        "aviation_risk_management"
    )
    # Production deployments must override this development-only value.
    jwt_secret_key: str = "dev-change-me-use-env-secret-in-production-32bytes"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    enable_x_user_id_auth_fallback: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
