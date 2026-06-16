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
        env_ignore_empty=True,   # empty string env vars fall back to field defaults
    )

    # LLM
    google_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: Literal["google", "anthropic", "openai"] = "google"
    llm_model: str = ""  # Must be set in .env — e.g. gemini-2.5-flash-lite or claude-haiku-4-5-20251001

    # Auth (JWT)
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Demo user (seeded on startup — see ADR-004)
    demo_email: str = "demo@example.com"
    demo_password: str = "demo1234"

    # Database
    # Local:      sqlite:///./data/market_research.db
    # Production: sqlite:////app/data/market_research.db  (Azure File Share mount)
    database_url: str = "sqlite:///./data/market_research.db"

    # CORS — comma-separated list of allowed origins
    # Local:      http://localhost:5173
    # Production: https://<your-static-web-app>.azurestaticapps.net
    allowed_origins: str = "http://localhost:5173"

    # Pipeline performance tuning (see ADR-005)
    pipeline_max_article_chars: int = 3000   # Truncate article text before summarizer
    pipeline_max_source_chars: int = 2000    # Truncate source text sent to judge
    pipeline_max_judge_claims: int = 3       # Max sequential judge LLM calls per run
    pipeline_max_themes: int = 2             # Max themes requested from summarizer
    pipeline_max_competitor_activities: int = 2  # Max competitor activities requested
    pipeline_hallucination_threshold: float = 0.95  # Min confidence to flag as hallucination

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # App
    app_env: Literal["local", "production"] = "local"
    enable_docs: bool = True  # Set ENABLE_DOCS=false to hide Swagger in production

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