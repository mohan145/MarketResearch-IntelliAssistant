import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Market Research Intelligence Assistant",
    description="Collect, analyze, and summarize market intelligence from public sources.",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
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

    init_db()
    logger.info("Database initialized. App env: %s", settings.app_env)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Health check endpoint used by Azure Container Apps and docker-compose."""
    return {"status": "ok", "env": settings.app_env}


# Register routers
from src.backend.api import auth, research

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(research.router, prefix="/api/research", tags=["research"])