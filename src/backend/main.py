import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import get_settings

# Read settings once at module load — env vars injected by Azure are available at this point
# because the container process starts fresh (no .env file overriding them in production).
settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Market Research Intelligence Assistant",
    description=(
        "Collect, analyze, and summarize market intelligence from public sources.\n\n"
        "## Authentication\n"
        "All `/api/research` endpoints require a **Bearer token**. "
        "Obtain one via `POST /auth/login` using the seeded demo credentials. "
        "The `/api/research/run` SSE endpoint accepts the token as a `?token=` query param "
        "because the browser EventSource API cannot set custom headers.\n\n"
        "## Pipeline flow\n"
        "`/api/research/run` streams Server-Sent Events as it works through three stages:\n"
        "1. **Scraping** — fetches each URL with httpx + trafilatura\n"
        "2. **Summarizing** — LangChain + Gemini produces an executive summary, key themes, "
        "and competitor activity cards\n"
        "3. **Judging** — LLM-as-a-judge verifies each claim against source text and flags "
        "hallucinations above the confidence threshold\n\n"
        "Demo credentials: `demo@example.com` / `demo1234`"
    ),
    version="0.1.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_tags=[
        {
            "name": "auth",
            "description": "Login and token management. Returns a 24-hour JWT Bearer token.",
        },
        {
            "name": "research",
            "description": (
                "Run market research analysis and retrieve history. "
                "The `/run` endpoint streams live progress via Server-Sent Events."
            ),
        },
        {
            "name": "system",
            "description": "Health check used by Azure Container Apps and docker-compose.",
        },
    ],
)

app.add_middleware(

    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_origin_regex=r"http://localhost.*",
)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database tables on first run."""
    from src.backend.database import init_db

    if not settings.llm_model:
        raise RuntimeError("LLM_MODEL is not set. Example: LLM_MODEL=gemini-2.5-flash-lite")

    # Validate API key for the configured provider at startup — fail fast with a clear message
    provider = settings.llm_provider
    if provider == "google" and not settings.google_api_key:
        raise RuntimeError(
            "LLM_PROVIDER=google but GOOGLE_API_KEY is not set. "
            "Add it to .env or Azure Container Apps secrets."
        )
    elif provider == "anthropic" and not settings.anthropic_api_key:
        raise RuntimeError(
            "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
            "Add it to .env or Azure Container Apps secrets."
        )
    elif provider == "openai" and not settings.openai_api_key:
        raise RuntimeError(
            "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
            "Add it to .env or Azure Container Apps secrets."
        )

    init_db()
    logger.info("Database initialized. App env: %s, LLM: %s/%s",
                settings.app_env, settings.llm_provider, settings.llm_model)


@app.get("/health", tags=["system"], summary="Health check")
async def health() -> dict[str, str]:
    """Returns `{"status": "ok"}` when the app is running.

    Used by Azure Container Apps liveness probes and docker-compose healthchecks.
    Also confirms which environment (`local` or `production`) is active.
    """
    return {"status": "ok", "env": settings.app_env}


# Register routers
from src.backend.api import auth, research

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(research.router, prefix="/api/research", tags=["research"])