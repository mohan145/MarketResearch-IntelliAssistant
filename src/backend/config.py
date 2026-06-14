from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file.

    Local: values come from .env file in project root.
    Production: values injected as environment variables (Azure Container Apps secrets).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # LLM
    google_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: Literal["google", "anthropic", "openai"] = "google"
    llm_model: str = "gemini-1.5-flash"

    # Auth (JWT)
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Database
    # Local:      sqlite:///./data/market_research.db
    # Production: sqlite:////app/data/market_research.db  (Azure File Share mount)
    database_url: str = "sqlite:///./data/market_research.db"

    # CORS — comma-separated list of allowed origins
    # Local:      http://localhost:5173
    # Production: https://<your-static-web-app>.azurestaticapps.net
    allowed_origins: str = "http://localhost:5173"

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # App
    app_env: Literal["local", "production"] = "local"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """True when running in Azure Container Apps."""
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance.

    Use as a FastAPI dependency: Depends(get_settings).
    Cache ensures .env is only read once per process.
    """
    return Settings()


settings = get_settings()