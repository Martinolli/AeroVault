"""Application settings loaded from environment variables (AEROVAULT_ prefix)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AEROVAULT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "dev"
    data_dir: str = "/data"
    openai_api_key: str | None = None
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    cors_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]


settings = Settings()
