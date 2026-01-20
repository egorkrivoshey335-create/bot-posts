"""Application configuration using pydantic-settings."""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Bot settings
    bot_token: str
    channel_id: str | int
    admin_ids: List[int] = []

    # Database settings
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "botuser"
    postgres_password: str = "botpassword"
    postgres_db: str = "bot_posts"

    # Logging
    log_level: str = "INFO"

    # Timezone
    tz: str = "Europe/Moscow"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        """Parse comma-separated admin IDs."""
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @field_validator("channel_id", mode="before")
    @classmethod
    def parse_channel_id(cls, v):
        """Parse channel ID (can be username or numeric ID)."""
        if isinstance(v, str):
            # If it's a numeric string, convert to int
            if v.lstrip("-").isdigit():
                return int(v)
        return v

    @property
    def database_url(self) -> str:
        """Build PostgreSQL connection URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Build synchronous PostgreSQL URL for Alembic."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
