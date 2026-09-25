"""
Project P4: 12-Factor Application Configuration via Pydantic Settings
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "Production AI & Task Backend"
    environment: str = Field(default="development", alias="ENV")
    debug: bool = False
    database_url: str = Field(
        default="sqlite+aiosqlite:///./prod_backend.db",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    jwt_secret_key: str = Field(
        default="super-secret-production-signing-key-change-me",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
