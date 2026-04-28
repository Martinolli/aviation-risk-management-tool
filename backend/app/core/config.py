from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "aviation-risk-management-tool"
    database_url: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/"
        "aviation_risk_management"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
